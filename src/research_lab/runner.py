from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from .benchmark import DeterministicValidator
from .contracts import ContractError, WorkerContract, parse_worker_contract
from .domain import CampaignSpec, Lesson, SchedulerDecision, TaskSpec, utc_now
from .scheduler import SchedulerPolicy
from .store import ResearchStore
from .workers import WorkerBackend


def _canonical_hash(value: dict[str, Any]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _run_id(campaign_id: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{campaign_id}-{timestamp}-{uuid.uuid4().hex[:8]}"


def _best_score(attempts: list[dict[str, Any]], task_id: str) -> float | None:
    scores = [
        float(attempt["validation"]["score"])
        for attempt in attempts
        if attempt["task_id"] == task_id
        and attempt.get("validation", {}).get("valid")
        and attempt["validation"].get("score") is not None
    ]
    return min(scores) if scores else None


def _lesson_from_contract(
    *,
    contract: WorkerContract,
    run_id: str,
    attempt_id: str,
    task_id: str,
) -> Lesson | None:
    if contract.lesson is None:
        return None
    digest = hashlib.sha256(
        json.dumps(
            {
                "statement": contract.lesson.statement,
                "tags": contract.lesson.tags,
                "task_id": task_id,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return Lesson(
        id=f"lesson-{digest}",
        statement=contract.lesson.statement,
        tags=contract.lesson.tags,
        evidence=contract.lesson.evidence,
        source_run_id=run_id,
        source_attempt_id=attempt_id,
        source_task_id=task_id,
        created_at=utc_now(),
    )


class CampaignRunner:
    def __init__(
        self,
        *,
        store: ResearchStore,
        worker: WorkerBackend,
        scheduler: SchedulerPolicy,
        validator: DeterministicValidator | None = None,
    ):
        self.store = store
        self.worker = worker
        self.scheduler = scheduler
        self.validator = validator or DeterministicValidator()

    def run(
        self,
        campaign: CampaignSpec,
        *,
        resume_run_id: str | None = None,
        max_new_attempts: int | None = None,
    ) -> tuple[str, str]:
        if max_new_attempts is not None and max_new_attempts < 1:
            raise ValueError("max_new_attempts must be at least 1")
        lock = getattr(self.store, "controller_lock", None)
        if callable(lock):
            with lock():
                return self._run_locked(
                    campaign,
                    resume_run_id=resume_run_id,
                    max_new_attempts=max_new_attempts,
                )
        return self._run_locked(
            campaign,
            resume_run_id=resume_run_id,
            max_new_attempts=max_new_attempts,
        )

    def _run_locked(
        self,
        campaign: CampaignSpec,
        *,
        resume_run_id: str | None,
        max_new_attempts: int | None,
    ) -> tuple[str, str]:
        if resume_run_id:
            run_id = resume_run_id
            manifest = self.store.read_run_manifest(run_id)
            manifest_campaign = manifest.get("campaign")
            if (
                not isinstance(manifest_campaign, dict)
                or _canonical_hash(manifest_campaign)
                != _canonical_hash(campaign.to_dict())
            ):
                raise ValueError(
                    "resume campaign does not match the immutable run manifest"
                )
            expected_scheduler = {
                "name": self.scheduler.name,
                "version": self.scheduler.version,
            }
            if manifest.get("scheduler") != expected_scheduler:
                raise ValueError(
                    "resume scheduler does not match the immutable run manifest"
                )
        else:
            run_id = _run_id(campaign.id)
            manifest = {
                "schema_version": 1,
                "id": run_id,
                "campaign": campaign.to_dict(),
                "scheduler": {
                    "name": self.scheduler.name,
                    "version": self.scheduler.version,
                },
                "created_at": utc_now(),
                "storage_contract": "single-controller-file-lock",
            }
            self.store.create_run(run_id, manifest)

        attempts = self.store.list_attempts(run_id)
        sequences = [int(attempt["sequence"]) for attempt in attempts]
        if len(sequences) != len(set(sequences)):
            raise ValueError(f"run {run_id} contains duplicate attempt sequences")
        if any(sequence < 1 or sequence > campaign.attempt_budget for sequence in sequences):
            raise ValueError(f"run {run_id} contains an out-of-budget attempt sequence")

        attempts_completed_this_invocation = 0
        if resume_run_id:
            attempts_completed_this_invocation = self._reconcile_incomplete_attempts(
                campaign=campaign,
                run_id=run_id,
                attempts=attempts,
                max_attempts=max_new_attempts,
            )

        completed_sequences = {int(attempt["sequence"]) for attempt in attempts}
        for sequence in range(1, campaign.attempt_budget + 1):
            if sequence in completed_sequences:
                continue
            if (
                max_new_attempts is not None
                and attempts_completed_this_invocation >= max_new_attempts
            ):
                break
            task, decision = self.scheduler.choose(
                campaign.tasks,
                attempts,
                self.store,
            )
            record = self._execute_attempt(
                campaign=campaign,
                run_id=run_id,
                sequence=sequence,
                task=task,
                decision=decision,
                attempts_before=attempts,
            )
            attempts.append(record)
            completed_sequences.add(sequence)
            attempts_completed_this_invocation += 1

        attempts.sort(key=lambda attempt: int(attempt["sequence"]))
        report = build_report(campaign, run_id, attempts)
        self.store.write_report(run_id, report)
        return run_id, report

    def _reconcile_incomplete_attempts(
        self,
        *,
        campaign: CampaignSpec,
        run_id: str,
        attempts: list[dict[str, Any]],
        max_attempts: int | None = None,
    ) -> int:
        completed_ids = {str(attempt["id"]) for attempt in attempts}
        grouped: dict[str, list[dict[str, Any]]] = {}
        for event in self.store.list_lifecycle_events(run_id):
            attempt_id = str(event.get("attempt_id", ""))
            if attempt_id and attempt_id not in completed_ids:
                grouped.setdefault(attempt_id, []).append(event)

        task_by_id = {task.id: task for task in campaign.tasks}
        pending: list[
            tuple[int, str, TaskSpec, SchedulerDecision, list[dict[str, Any]]]
        ] = []
        for attempt_id, events in grouped.items():
            selected = next(
                (
                    event
                    for event in events
                    if event.get("kind") == "attempt_selected"
                ),
                None,
            )
            if selected is None:
                raise ValueError(
                    f"incomplete attempt {attempt_id} has no selection event"
                )
            payload = selected.get("payload", {})
            sequence = int(payload["sequence"])
            task_id = str(payload["task_id"])
            decision_data = payload["scheduler_decision"]
            if task_id not in task_by_id:
                raise ValueError(
                    f"incomplete attempt {attempt_id} references unknown task {task_id}"
                )
            decision = SchedulerDecision(
                policy=str(decision_data["policy"]),
                policy_version=str(decision_data["policy_version"]),
                task_id=str(decision_data["task_id"]),
                rationale=str(decision_data["rationale"]),
                retrieved_lesson_ids=tuple(
                    str(item)
                    for item in decision_data.get("retrieved_lesson_ids", [])
                ),
            )
            pending.append(
                (sequence, attempt_id, task_by_id[task_id], decision, events)
            )

        occupied_sequences = {int(attempt["sequence"]) for attempt in attempts}
        reconciled = 0
        for sequence, attempt_id, task, decision, events in sorted(pending):
            if max_attempts is not None and reconciled >= max_attempts:
                break
            if sequence in occupied_sequences:
                raise ValueError(
                    f"incomplete attempt {attempt_id} conflicts at sequence {sequence}"
                )
            record = self._execute_attempt(
                campaign=campaign,
                run_id=run_id,
                sequence=sequence,
                task=task,
                decision=decision,
                attempts_before=attempts,
                attempt_id=attempt_id,
                existing_events=events,
            )
            attempts.append(record)
            occupied_sequences.add(sequence)
            reconciled += 1
        return reconciled

    def _execute_attempt(
        self,
        *,
        campaign: CampaignSpec,
        run_id: str,
        sequence: int,
        task: TaskSpec,
        decision: SchedulerDecision,
        attempts_before: list[dict[str, Any]],
        attempt_id: str | None = None,
        existing_events: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        existing_events = existing_events or []
        attempt_id = attempt_id or f"attempt-{sequence:04d}-{uuid.uuid4().hex[:8]}"
        selected_lesson_ids = set(decision.retrieved_lesson_ids)
        lessons = [
            lesson
            for lesson in self.store.find_lessons(task.tags, limit=3)
            if lesson.id in selected_lesson_ids
        ]
        selected_event = next(
            (
                event
                for event in existing_events
                if event.get("kind") == "attempt_selected"
            ),
            None,
        )
        started_at = (
            str(selected_event.get("recorded_at"))
            if selected_event and selected_event.get("recorded_at")
            else utc_now()
        )
        lifecycle_sequence = max(
            (
                int(str(event.get("id", "0")).split("-", 1)[0])
                for event in existing_events
                if str(event.get("id", "")).split("-", 1)[0].isdigit()
            ),
            default=0,
        )

        def on_lifecycle(kind: str, payload: dict[str, Any]) -> None:
            nonlocal lifecycle_sequence
            lifecycle_sequence += 1
            self.store.append_lifecycle_event(
                run_id,
                attempt_id,
                {
                    "schema_version": 1,
                    "id": f"{lifecycle_sequence:04d}-{kind}",
                    "run_id": run_id,
                    "attempt_id": attempt_id,
                    "kind": kind,
                    "recorded_at": utc_now(),
                    "payload": payload,
                },
            )

        if not existing_events:
            on_lifecycle(
                "attempt_selected",
                {
                    "sequence": sequence,
                    "task_id": task.id,
                    "scheduler_decision": decision.to_dict(),
                },
            )
        else:
            on_lifecycle(
                "attempt_recovery_started",
                {
                    "sequence": sequence,
                    "prior_lifecycle_events": len(existing_events),
                },
            )

        execution = None
        try:
            recover = getattr(self.worker, "recover", None)
            has_remote_state = any(
                event.get("kind")
                in {
                    "start_task_created",
                    "conversation_ready",
                    "conversation_running",
                }
                for event in existing_events
            )
            if existing_events and has_remote_state:
                if not callable(recover):
                    raise RuntimeError(
                        "interrupted attempt has remote state but its worker "
                        "does not implement recovery"
                    )
                execution = recover(
                    campaign=campaign,
                    task=task,
                    run_id=run_id,
                    attempt_id=attempt_id,
                    lessons=lessons,
                    lifecycle_events=existing_events,
                    on_lifecycle=on_lifecycle,
                )
            else:
                execution = self.worker.execute(
                    campaign=campaign,
                    task=task,
                    run_id=run_id,
                    attempt_id=attempt_id,
                    lessons=lessons,
                    on_lifecycle=on_lifecycle,
                )
            contract = parse_worker_contract(execution.final_text)
            record = self._record_successful_execution(
                run_id=run_id,
                attempt_id=attempt_id,
                sequence=sequence,
                task=task,
                decision=decision,
                attempts_before=attempts_before,
                started_at=started_at,
                execution=execution,
                contract=contract,
            )
        except (ContractError, TimeoutError, RuntimeError, ValueError) as exc:
            on_lifecycle(
                "attempt_failed",
                {"type": type(exc).__name__, "message": str(exc)[:1000]},
            )
            record = {
                "schema_version": 1,
                "id": attempt_id,
                "run_id": run_id,
                "sequence": sequence,
                "task_id": task.id,
                "started_at": started_at,
                "finished_at": utc_now(),
                "scheduler_decision": decision.to_dict(),
                "retrieved_lesson_ids": [lesson.id for lesson in lessons],
                "worker_kind": (
                    execution.worker_kind if execution is not None else None
                ),
                "conversation": (
                    execution.conversation if execution is not None else {}
                ),
                "metadata": execution.metadata if execution is not None else {},
                "final_response": (
                    {
                        "sha256": hashlib.sha256(
                            execution.final_text.encode("utf-8")
                        ).hexdigest(),
                        "length": len(execution.final_text),
                    }
                    if execution is not None
                    else None
                ),
                "outcome": "failed",
                "failure": {
                    "type": type(exc).__name__,
                    "message": str(exc)[:1000],
                },
                "validation": {"valid": False, "score": None, "errors": []},
            }
        self.store.append_attempt(run_id, record)
        on_lifecycle(
            "attempt_recorded",
            {
                "outcome": record.get("outcome"),
                "validation_valid": record.get("validation", {}).get("valid"),
            },
        )
        return record

    def _record_successful_execution(
        self,
        *,
        run_id: str,
        attempt_id: str,
        sequence: int,
        task: TaskSpec,
        decision: SchedulerDecision,
        attempts_before: list[dict[str, Any]],
        started_at: str,
        execution: Any,
        contract: WorkerContract,
    ) -> dict[str, Any]:
        validation = (
            self.validator.validate(task, contract.candidate or {})
            if contract.status == "done"
            else None
        )
        candidate_hash = (
            _canonical_hash(contract.candidate)
            if contract.candidate is not None
            else None
        )
        prior_hashes = {
            attempt.get("candidate_hash")
            for attempt in attempts_before
            if attempt.get("candidate_hash") and attempt.get("task_id") == task.id
        }
        prior_best = _best_score(attempts_before, task.id)
        improved = bool(
            validation
            and validation.valid
            and validation.score is not None
            and (prior_best is None or validation.score < prior_best)
        )
        promoted_lesson_id: str | None = None
        if improved:
            lesson = _lesson_from_contract(
                contract=contract,
                run_id=run_id,
                attempt_id=attempt_id,
                task_id=task.id,
            )
            if lesson:
                self.store.save_validated_lesson(lesson)
                promoted_lesson_id = lesson.id

        return {
            "schema_version": 1,
            "id": attempt_id,
            "run_id": run_id,
            "sequence": sequence,
            "task_id": task.id,
            "started_at": started_at,
            "finished_at": utc_now(),
            "worker_kind": execution.worker_kind,
            "scheduler_decision": decision.to_dict(),
            "retrieved_lesson_ids": decision.to_dict()["retrieved_lesson_ids"],
            "conversation": execution.conversation,
            "metadata": execution.metadata,
            "final_response": {
                "sha256": hashlib.sha256(
                    execution.final_text.encode("utf-8")
                ).hexdigest(),
                "length": len(execution.final_text),
            },
            "contract": {
                "status": contract.status,
                "summary": list(contract.summary),
                "next_gate": contract.next_gate,
                "transport": contract.transport,
                "transport_compliant": contract.transport == "exact-json",
            },
            "candidate": contract.candidate,
            "candidate_hash": candidate_hash,
            "duplicate_candidate": candidate_hash in prior_hashes if candidate_hash else False,
            "validation": (
                validation.to_dict()
                if validation
                else {"valid": False, "score": None, "errors": ["worker did not request validation"]}
            ),
            "improved": improved,
            "promoted_lesson_id": promoted_lesson_id,
            "outcome": "completed" if contract.status == "done" else contract.status,
        }


def build_report(
    campaign: CampaignSpec,
    run_id: str,
    attempts: list[dict[str, Any]],
) -> str:
    completed = [attempt for attempt in attempts if attempt.get("outcome") == "completed"]
    valid = [attempt for attempt in completed if attempt.get("validation", {}).get("valid")]
    duplicates = [attempt for attempt in attempts if attempt.get("duplicate_candidate")]
    task_counts = Counter(str(attempt["task_id"]) for attempt in attempts)
    lines = [
        f"# Research run: {run_id}",
        "",
        f"- Campaign: {campaign.name}",
        f"- Scheduler: {campaign.policy}",
        f"- Attempt budget: {campaign.attempt_budget}",
        f"- Attempts recorded: {len(attempts)}",
        f"- Valid candidates: {len(valid)}",
        f"- Duplicate candidates: {len(duplicates)}",
        f"- Normalized solution quality: {_normalized_quality(campaign, attempts):.3f}",
        "",
        "## Task results",
        "",
        "| Task | Attempts | Best score |",
        "| --- | ---: | ---: |",
    ]
    for task in campaign.tasks:
        best = _best_score(attempts, task.id)
        best_text = "none" if best is None else f"{best:g}"
        lines.append(f"| {task.id} | {task_counts[task.id]} | {best_text} |")
    lines.extend(
        [
            "",
            "## Attempt ledger",
            "",
            "| Sequence | Task | Worker | Outcome | Valid | Score | Improved | Duplicate | Conversation |",
            "| ---: | --- | --- | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for attempt in attempts:
        validation = attempt.get("validation", {})
        score = validation.get("score")
        score_text = "—" if score is None else f"{float(score):g}"
        conversation = attempt.get("conversation", {})
        url = conversation.get("ui_url")
        link = f"[open]({url})" if url else "—"
        lines.append(
            "| {sequence} | {task} | {worker} | {outcome} | {valid} | {score} | "
            "{improved} | {duplicate} | {conversation} |".format(
                sequence=attempt["sequence"],
                task=attempt["task_id"],
                worker=attempt.get("worker_kind", "—"),
                outcome=attempt.get("outcome", "unknown"),
                valid="yes" if validation.get("valid") else "no",
                score=score_text,
                improved="yes" if attempt.get("improved") else "no",
                duplicate="yes" if attempt.get("duplicate_candidate") else "no",
                conversation=link,
            )
        )
    lines.extend(
        [
            "",
            "This report is derived from immutable attempt records. Worker claims are",
            "not treated as validation evidence.",
        ]
    )
    return "\n".join(lines) + "\n"


def _normalized_quality(
    campaign: CampaignSpec,
    attempts: list[dict[str, Any]],
) -> float:
    """Return mean target/best score, with unsolved tasks contributing zero."""
    qualities: list[float] = []
    for task in campaign.tasks:
        best = _best_score(attempts, task.id)
        if best is None:
            qualities.append(0.0)
        elif task.target_score is None:
            qualities.append(1.0)
        elif best <= 0:
            qualities.append(0.0)
        else:
            qualities.append(min(1.0, task.target_score / best))
    return sum(qualities) / len(qualities)

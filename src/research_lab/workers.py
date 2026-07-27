from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from typing import Any, Protocol

from .domain import CampaignSpec, Lesson, TaskSpec, WorkerExecution
from .openhands import OpenHandsCapacityError, OpenHandsClient, sanitize_metadata


class WorkerBackend(Protocol):
    def execute(
        self,
        *,
        campaign: CampaignSpec,
        task: TaskSpec,
        run_id: str,
        attempt_id: str,
        lessons: list[Lesson],
        on_lifecycle: Callable[[str, dict[str, Any]], None],
    ) -> WorkerExecution: ...


def _greedy_coloring(task: TaskSpec, *, use_validated_memory: bool) -> dict[str, int]:
    adjacency: dict[str, set[str]] = {node: set() for node in task.nodes}
    for left, right in task.edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    order = (
        sorted(task.nodes, key=lambda node: (-len(adjacency[node]), node))
        if use_validated_memory
        else list(task.nodes)
    )
    assignments: dict[str, int] = {}
    for node in order:
        used = {assignments[neighbor] for neighbor in adjacency[node] if neighbor in assignments}
        color = 0
        while color in used:
            color += 1
        assignments[node] = color
    return assignments


def _set_cover(task: TaskSpec, *, use_validated_memory: bool) -> list[str]:
    universe = {str(item) for item in task.payload["universe"]}
    sets = {
        str(set_id): {str(item) for item in members}
        for set_id, members in task.payload["sets"].items()
    }
    uncovered = set(universe)
    selected: list[str] = []
    remaining = dict(sets)
    while uncovered:
        if use_validated_memory:
            set_id = min(
                remaining,
                key=lambda item: (-len(remaining[item] & uncovered), item),
            )
        else:
            set_id = next(iter(remaining))
        contribution = remaining.pop(set_id) & uncovered
        if contribution:
            selected.append(set_id)
            uncovered -= contribution
        if not remaining and uncovered:
            break
    return selected


def _bin_pack(task: TaskSpec, *, use_validated_memory: bool) -> list[list[str]]:
    capacity = float(task.payload["capacity"])
    items = [(str(item), float(weight)) for item, weight in task.payload["items"].items()]
    if use_validated_memory:
        items.sort(key=lambda item: (-item[1], item[0]))
        bins: list[list[str]] = []
        loads: list[float] = []
        for item_id, weight in items:
            for index, load in enumerate(loads):
                if load + weight <= capacity:
                    bins[index].append(item_id)
                    loads[index] += weight
                    break
            else:
                bins.append([item_id])
                loads.append(weight)
        return bins

    bins = []
    load = 0.0
    for item_id, weight in items:
        if not bins or load + weight > capacity:
            bins.append([item_id])
            load = weight
        else:
            bins[-1].append(item_id)
            load += weight
    return bins


class LocalHeuristicWorker:
    """Deterministic offline worker used to validate the complete control path."""

    def execute(
        self,
        *,
        campaign: CampaignSpec,
        task: TaskSpec,
        run_id: str,
        attempt_id: str,
        lessons: list[Lesson],
        on_lifecycle: Callable[[str, dict[str, Any]], None],
    ) -> WorkerExecution:
        on_lifecycle("worker_started", {"worker_kind": "local"})
        lesson_text = " ".join(lesson.statement.lower() for lesson in lessons)
        if task.family == "graph-coloring":
            use_validated_memory = "high-degree" in lesson_text
            candidate = {
                "assignments": _greedy_coloring(
                    task,
                    use_validated_memory=use_validated_memory,
                )
            }
            lesson = {
                "statement": "Assign high-degree vertices before lower-degree vertices.",
                "tags": ["graph-coloring", *task.tags],
                "evidence": "The deterministic largest-degree-first candidate passed to validation.",
            }
            summary = f"Colored {len(task.nodes)} nodes."
            algorithm = (
                "largest-degree-first" if use_validated_memory else "input-order-greedy"
            )
        elif task.family == "set-cover":
            use_validated_memory = "most uncovered" in lesson_text
            candidate = {
                "selected_sets": _set_cover(
                    task,
                    use_validated_memory=use_validated_memory,
                )
            }
            lesson = {
                "statement": "Choose the set covering the most uncovered elements first.",
                "tags": ["set-cover", *task.tags],
                "evidence": "The greedy marginal-coverage candidate passed to validation.",
            }
            summary = f"Covered {len(task.payload['universe'])} elements."
            algorithm = (
                "largest-marginal-coverage"
                if use_validated_memory
                else "input-order-cover"
            )
        elif task.family == "bin-packing":
            use_validated_memory = "largest items first" in lesson_text
            candidate = {
                "bins": _bin_pack(
                    task,
                    use_validated_memory=use_validated_memory,
                )
            }
            lesson = {
                "statement": "Place the largest items first, using the first bin with room.",
                "tags": ["bin-packing", *task.tags],
                "evidence": "The first-fit-decreasing candidate passed to validation.",
            }
            summary = f"Packed {len(task.payload['items'])} items."
            algorithm = (
                "first-fit-decreasing" if use_validated_memory else "next-fit-input-order"
            )
        else:
            raise ValueError(f"unsupported local worker family: {task.family}")
        contract = {
            "status": "done",
            "candidate": candidate,
            "lesson": lesson,
            "summary": [
                summary,
                f"Received {len(lessons)} validated lessons.",
            ],
            "next_gate": "validate",
        }
        execution = WorkerExecution(
            final_text=json.dumps(contract, sort_keys=True),
            worker_kind="local",
            metadata={
                "algorithm": algorithm,
                "used_validated_memory": use_validated_memory,
            },
        )
        on_lifecycle("final_response_ready", {"worker_kind": "local"})
        return execution


def render_worker_prompt(
    *,
    campaign: CampaignSpec,
    task: TaskSpec,
    run_id: str,
    attempt_id: str,
    lessons: list[Lesson],
) -> str:
    lesson_payload = [
        {
            "id": lesson.id,
            "statement": lesson.statement,
            "tags": list(lesson.tags),
            "evidence": lesson.evidence,
        }
        for lesson in lessons
    ]
    task_payload: dict[str, Any] = {
        "id": task.id,
        "family": task.family,
        "description": task.description,
        "tags": list(task.tags),
    }
    if task.family == "graph-coloring":
        task_payload.update(
            {
                "nodes": list(task.nodes),
                "edges": [list(edge) for edge in task.edges],
            }
        )
        objective = """Produce a graph-color assignment using as few colors as possible. Every node
must be assigned, and adjacent nodes must have different colors."""
        candidate_example: dict[str, Any] = {
            "assignments": {node: 0 for node in task.nodes}
        }
    elif task.family == "set-cover":
        task_payload["payload"] = task.payload
        objective = """Select as few named sets as possible while covering every element in the
universe. Return only set IDs defined by the task, with no duplicates."""
        candidate_example = {
            "selected_sets": [str(set_id) for set_id in task.payload["sets"]]
        }
    elif task.family == "bin-packing":
        task_payload["payload"] = task.payload
        objective = """Pack every named item exactly once into as few bins as possible. The sum of
item weights in each bin must not exceed the task capacity."""
        candidate_example = {
            "bins": [[str(item_id)] for item_id in task.payload["items"]]
        }
    else:
        raise ValueError(f"unsupported worker prompt family: {task.family}")
    contract_example = {
        "status": "done",
        "candidate": candidate_example,
        "lesson": {
            "statement": "One concise, reusable claim.",
            "tags": [task.family],
            "evidence": "What this attempt observed; validation happens outside this worker.",
        },
        "summary": ["Five or fewer concise strings."],
        "next_gate": "validate",
    }
    research_protocol = ""
    if campaign.research_protocol == "endurance-v1":
        research_protocol = """
Endurance research protocol:
- Use terminal tools and a temporary directory outside the repository. Do not
  edit or commit repository files.
- Implement and compare at least three solution approaches appropriate to this
  task family: an exact or exhaustive baseline, a standard greedy heuristic,
  and a seeded randomized or local-search refinement.
- Run deterministic correctness checks after each approach. Exercise at least
  30 seeded orderings or perturbations and record the best valid score.
- Identify one concrete case where the weakest approach makes a worse choice,
  then use that observation in the final refinement.
- Independently re-check every task constraint before returning the final
  candidate. Keep the complete attempt within twenty minutes.
- After the final candidate passes your own checks, run one controlled
  seven-minute wait using a terminal command before returning the contract.
  This dwell period is part of the controller endurance test, not additional
  research evidence. Do not perform more work or make network calls during it.
- Use the final summary strings to name the approaches compared, the number of
  trials completed, the best valid score, the final verification result, and
  completion of the controlled dwell period.
"""
    return f"""You are one bounded experimental worker in a research campaign.

Run ID: {run_id}
Attempt ID: {attempt_id}
Campaign: {campaign.id}
Repository: {campaign.repository or "none"}
Branch: {campaign.branch or "none"}

Objective:
{objective}

Task:
{json.dumps(task_payload, indent=2, sort_keys=True)}

Validated lessons selected by the external scheduler:
{json.dumps(lesson_payload, indent=2, sort_keys=True)}

{research_protocol}
Constraints:
- Work only on this task.
- Do not start other agents or conversations.
- Do not merge, deploy, or mutate production systems.
- Do not claim that your candidate is valid; an independent deterministic
  validator owns that decision.
- Copy node, set, and item IDs exactly as written in the task. Never add a
  prefix, suffix, or descriptive alias.
- Use JSON scalar color values.
- Your final response must be exactly one JSON object with no prose or fence.

Required final contract:
{json.dumps(contract_example, indent=2, sort_keys=True)}

If blocked, return the same five fields with status "needs-human", candidate
and lesson null, next_gate "human-review", and a concise summary.
"""


class OpenHandsWorker:
    def __init__(
        self,
        client: OpenHandsClient,
        *,
        start_timeout_seconds: int = 600,
        execution_timeout_seconds: int = 1800,
        poll_seconds: int = 10,
        pause_after_attempt: bool = True,
        pause_timeout_seconds: int = 120,
        runtime_limit: int = 10,
        launch_lock_at: int = 7,
    ):
        self.client = client
        self.start_timeout_seconds = start_timeout_seconds
        self.execution_timeout_seconds = execution_timeout_seconds
        self.poll_seconds = poll_seconds
        self.pause_after_attempt = pause_after_attempt
        self.pause_timeout_seconds = pause_timeout_seconds
        self.runtime_limit = runtime_limit
        self.launch_lock_at = launch_lock_at

    def execute(
        self,
        *,
        campaign: CampaignSpec,
        task: TaskSpec,
        run_id: str,
        attempt_id: str,
        lessons: list[Lesson],
        on_lifecycle: Callable[[str, dict[str, Any]], None],
    ) -> WorkerExecution:
        capacity = self.client.capacity_snapshot(
            runtime_limit=self.runtime_limit,
            launch_lock_at=self.launch_lock_at,
        )
        on_lifecycle("capacity_checked", capacity)
        if not capacity["launch_allowed"]:
            raise OpenHandsCapacityError(
                "OpenHands launch blocked: "
                f"{capacity['active']} active sandboxes meets or exceeds the "
                f"{capacity['launch_lock_at']} launch threshold"
            )
        on_lifecycle("worker_started", {"worker_kind": "openhands"})
        prompt = render_worker_prompt(
            campaign=campaign,
            task=task,
            run_id=run_id,
            attempt_id=attempt_id,
            lessons=lessons,
        )
        start = self.client.start_conversation(
            prompt=prompt,
            title=f"[research-lab] {run_id} / {task.id} / {attempt_id}",
            repository=campaign.repository,
            branch=campaign.branch,
            model=campaign.model,
        )
        start_task_id = str(start["id"])
        on_lifecycle("start_task_created", {"start_task_id": start_task_id})
        return self._complete_started_attempt(
            start_task_id=start_task_id,
            on_lifecycle=on_lifecycle,
        )

    def recover(
        self,
        *,
        campaign: CampaignSpec,
        task: TaskSpec,
        run_id: str,
        attempt_id: str,
        lessons: list[Lesson],
        lifecycle_events: list[dict[str, Any]],
        on_lifecycle: Callable[[str, dict[str, Any]], None],
    ) -> WorkerExecution:
        del campaign, task, run_id, attempt_id, lessons
        start_task_id = ""
        for event in lifecycle_events:
            if event.get("kind") == "start_task_created":
                start_task_id = str(
                    event.get("payload", {}).get("start_task_id", "")
                )
        if not start_task_id:
            raise RuntimeError(
                "OpenHands recovery requires a persisted start-task ID"
            )
        on_lifecycle(
            "openhands_recovery_attached",
            {"start_task_id": start_task_id},
        )
        return self._complete_started_attempt(
            start_task_id=start_task_id,
            on_lifecycle=on_lifecycle,
        )

    def _complete_started_attempt(
        self,
        *,
        start_task_id: str,
        on_lifecycle: Callable[[str, dict[str, Any]], None],
    ) -> WorkerExecution:
        try:
            ready = self.client.poll_start_task(
                start_task_id,
                timeout_seconds=self.start_timeout_seconds,
                poll_seconds=self.poll_seconds,
            )
        except Exception:
            try:
                failed_start = self.client.get_start_task(start_task_id)
            except Exception:
                failed_start = {}
            on_lifecycle(
                "conversation_start_failed",
                {
                    "start_task_id": start_task_id,
                    "status": failed_start.get("status"),
                    "detail": failed_start.get("detail"),
                    "sandbox_id": failed_start.get("sandbox_id"),
                },
            )
            raise
        conversation_id = str(ready["app_conversation_id"])
        sandbox_id = ready.get("sandbox_id")
        on_lifecycle(
            "conversation_ready",
            {
                "start_task_id": start_task_id,
                "conversation_id": conversation_id,
                "sandbox_id": sandbox_id,
                "ui_url": self.client.conversation_url(conversation_id),
            },
        )
        try:
            record, events, recovered = self.client.wait_for_terminal(
                conversation_id,
                timeout_seconds=self.execution_timeout_seconds,
                poll_seconds=self.poll_seconds,
            )
            sandbox_id = sandbox_id or record.get("sandbox_id")
            on_lifecycle(
                "conversation_terminal",
                {
                    "conversation_id": conversation_id,
                    "execution_status": record.get("execution_status"),
                    "sandbox_status": record.get("sandbox_status"),
                    "terminal_status_recovered_from_events": recovered,
                },
            )
            final_text, final_events = self.client.final_response(
                conversation_id,
                initial_events=events,
            )
            on_lifecycle(
                "final_response_ready",
                {
                    "conversation_id": conversation_id,
                    "present": bool(final_text),
                    "event_count": len(final_events),
                },
            )
            event_counts = Counter(
                str(event.get("kind", "unknown")) for event in final_events
            )
            conversation = {
                "start_task_id": start_task_id,
                "conversation_id": conversation_id,
                "sandbox_id": sandbox_id,
                "ui_url": self.client.conversation_url(conversation_id),
                "execution_status": record.get("execution_status"),
                "sandbox_status": record.get("sandbox_status"),
                "terminal_status_recovered_from_events": recovered,
            }
            metadata = {
                "conversation_snapshot": sanitize_metadata(record),
                "start_task_snapshot": sanitize_metadata(ready),
                "event_counts": dict(sorted(event_counts.items())),
                "event_count": len(final_events),
            }
            return WorkerExecution(
                final_text=final_text,
                worker_kind="openhands",
                conversation=conversation,
                metadata=metadata,
            )
        finally:
            if self.pause_after_attempt and sandbox_id:
                on_lifecycle(
                    "sandbox_pause_requested",
                    {
                        "conversation_id": conversation_id,
                        "sandbox_id": sandbox_id,
                    },
                )
                try:
                    paused = self.client.pause_sandbox(
                        str(sandbox_id),
                        timeout_seconds=self.pause_timeout_seconds,
                        poll_seconds=min(self.poll_seconds, 2),
                    )
                    on_lifecycle(
                        "sandbox_paused",
                        {
                            "conversation_id": conversation_id,
                            "sandbox_id": sandbox_id,
                            "sandbox_status": paused.get("status"),
                        },
                    )
                except (RuntimeError, TimeoutError, ValueError) as exc:
                    on_lifecycle(
                        "sandbox_pause_failed",
                        {
                            "conversation_id": conversation_id,
                            "sandbox_id": sandbox_id,
                            "type": type(exc).__name__,
                            "message": str(exc)[:1000],
                        },
                    )

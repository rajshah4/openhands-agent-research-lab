from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from typing import Any, Protocol

from .domain import CampaignSpec, Lesson, TaskSpec, WorkerExecution
from .openhands import OpenHandsClient, sanitize_metadata


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


def _greedy_coloring(task: TaskSpec) -> dict[str, int]:
    adjacency: dict[str, set[str]] = {node: set() for node in task.nodes}
    for left, right in task.edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    order = sorted(task.nodes, key=lambda node: (-len(adjacency[node]), node))
    assignments: dict[str, int] = {}
    for node in order:
        used = {assignments[neighbor] for neighbor in adjacency[node] if neighbor in assignments}
        color = 0
        while color in used:
            color += 1
        assignments[node] = color
    return assignments


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
        assignments = _greedy_coloring(task)
        contract = {
            "status": "done",
            "candidate": {"assignments": assignments},
            "lesson": {
                "statement": "Assign high-degree vertices before lower-degree vertices.",
                "tags": ["graph-coloring", *task.tags],
                "evidence": "The deterministic largest-degree-first candidate passed to validation.",
            },
            "summary": [
                f"Colored {len(task.nodes)} nodes.",
                f"Received {len(lessons)} validated lessons.",
            ],
            "next_gate": "validate",
        }
        execution = WorkerExecution(
            final_text=json.dumps(contract, sort_keys=True),
            worker_kind="local",
            metadata={"algorithm": "largest-degree-first"},
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
    task_payload = {
        "id": task.id,
        "family": task.family,
        "description": task.description,
        "tags": list(task.tags),
        "nodes": list(task.nodes),
        "edges": [list(edge) for edge in task.edges],
    }
    contract_example = {
        "status": "done",
        "candidate": {"assignments": {"0": 0}},
        "lesson": {
            "statement": "One concise, reusable claim.",
            "tags": ["graph-coloring"],
            "evidence": "What this attempt observed; validation happens outside this worker.",
        },
        "summary": ["Five or fewer concise strings."],
        "next_gate": "validate",
    }
    return f"""You are one bounded experimental worker in a research campaign.

Run ID: {run_id}
Attempt ID: {attempt_id}
Campaign: {campaign.id}
Repository: {campaign.repository or "none"}
Branch: {campaign.branch or "none"}

Objective:
Produce a graph-color assignment using as few colors as possible. Every node
must be assigned, and adjacent nodes must have different colors.

Task:
{json.dumps(task_payload, indent=2, sort_keys=True)}

Validated lessons selected by the external scheduler:
{json.dumps(lesson_payload, indent=2, sort_keys=True)}

Constraints:
- Work only on this task.
- Do not start other agents or conversations.
- Do not merge, deploy, or mutate production systems.
- Do not claim that your candidate is valid; an independent deterministic
  validator owns that decision.
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
    ):
        self.client = client
        self.start_timeout_seconds = start_timeout_seconds
        self.execution_timeout_seconds = execution_timeout_seconds
        self.poll_seconds = poll_seconds

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
        ready = self.client.poll_start_task(
            start_task_id,
            timeout_seconds=self.start_timeout_seconds,
            poll_seconds=self.poll_seconds,
        )
        conversation_id = str(ready["app_conversation_id"])
        on_lifecycle(
            "conversation_ready",
            {
                "start_task_id": start_task_id,
                "conversation_id": conversation_id,
                "sandbox_id": ready.get("sandbox_id"),
                "ui_url": self.client.conversation_url(conversation_id),
            },
        )
        record, events, recovered = self.client.wait_for_terminal(
            conversation_id,
            timeout_seconds=self.execution_timeout_seconds,
            poll_seconds=self.poll_seconds,
        )
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
        event_counts = Counter(str(event.get("kind", "unknown")) for event in final_events)
        conversation = {
            "start_task_id": start_task_id,
            "conversation_id": conversation_id,
            "sandbox_id": ready.get("sandbox_id") or record.get("sandbox_id"),
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

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class TaskSpec:
    id: str
    family: str
    description: str
    tags: tuple[str, ...]
    nodes: tuple[str, ...] = ()
    edges: tuple[tuple[str, str], ...] = ()
    target_score: float | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(cls, path: Path) -> "TaskSpec":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            id=str(data["id"]),
            family=str(data["family"]),
            description=str(data["description"]),
            tags=tuple(str(tag) for tag in data.get("tags", [])),
            nodes=tuple(str(node) for node in data.get("nodes", [])),
            edges=tuple(
                (str(edge[0]), str(edge[1])) for edge in data.get("edges", [])
            ),
            target_score=(
                float(data["target_score"])
                if data.get("target_score") is not None
                else None
            ),
            payload=dict(data.get("payload", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CampaignSpec:
    id: str
    name: str
    policy: str
    attempt_budget: int
    repository: str | None
    branch: str | None
    model: str | None
    tasks: tuple[TaskSpec, ...]
    research_protocol: str | None = None

    @classmethod
    def from_path(cls, path: Path) -> "CampaignSpec":
        data = json.loads(path.read_text(encoding="utf-8"))
        tasks = tuple(
            TaskSpec.from_path((path.parent / task_path).resolve())
            for task_path in data["task_paths"]
        )
        if not tasks:
            raise ValueError("campaign must contain at least one task")
        budget = int(data["attempt_budget"])
        if budget < 1:
            raise ValueError("attempt_budget must be at least 1")
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            policy=str(data.get("policy", "managed")),
            attempt_budget=budget,
            repository=data.get("repository"),
            branch=data.get("branch"),
            model=data.get("model"),
            tasks=tasks,
            research_protocol=data.get("research_protocol"),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.research_protocol is None:
            data.pop("research_protocol")
        return data


@dataclass(frozen=True)
class Lesson:
    id: str
    statement: str
    tags: tuple[str, ...]
    evidence: str
    source_run_id: str
    source_attempt_id: str
    source_task_id: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SchedulerDecision:
    policy: str
    policy_version: str
    task_id: str
    rationale: str
    retrieved_lesson_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkerExecution:
    final_text: str
    worker_kind: str
    conversation: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    score: float | None
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

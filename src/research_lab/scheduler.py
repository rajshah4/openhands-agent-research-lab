from __future__ import annotations

import math
from collections import Counter
from typing import Any

from .domain import SchedulerDecision, TaskSpec
from .store import ResearchStore


class SchedulerPolicy:
    name = "base"
    version = "1"

    def choose(
        self,
        tasks: tuple[TaskSpec, ...],
        attempts: list[dict[str, Any]],
        store: ResearchStore,
    ) -> tuple[TaskSpec, SchedulerDecision]:
        raise NotImplementedError


class RoundRobinPolicy(SchedulerPolicy):
    name = "round_robin"

    def choose(
        self,
        tasks: tuple[TaskSpec, ...],
        attempts: list[dict[str, Any]],
        store: ResearchStore,
    ) -> tuple[TaskSpec, SchedulerDecision]:
        counts = Counter(str(attempt["task_id"]) for attempt in attempts)
        task = min(tasks, key=lambda item: (counts[item.id], item.id))
        return task, SchedulerDecision(
            policy=self.name,
            policy_version=self.version,
            task_id=task.id,
            rationale="selected the task with the fewest recorded attempts",
        )


class ManagedPolicy(SchedulerPolicy):
    name = "managed"

    def choose(
        self,
        tasks: tuple[TaskSpec, ...],
        attempts: list[dict[str, Any]],
        store: ResearchStore,
    ) -> tuple[TaskSpec, SchedulerDecision]:
        counts = Counter(str(attempt["task_id"]) for attempt in attempts)
        valid_scores: dict[str, list[float]] = {task.id: [] for task in tasks}
        for attempt in attempts:
            validation = attempt.get("validation") or {}
            if validation.get("valid") and validation.get("score") is not None:
                valid_scores[str(attempt["task_id"])].append(float(validation["score"]))

        def priority(task: TaskSpec) -> tuple[int, int, float, str]:
            unattempted = 0 if counts[task.id] == 0 else 1
            best = min(valid_scores[task.id]) if valid_scores[task.id] else math.inf
            return (unattempted, counts[task.id], -best, task.id)

        task = min(tasks, key=priority)
        lessons = store.find_lessons(task.tags, limit=3)
        return task, SchedulerDecision(
            policy=self.name,
            policy_version=self.version,
            task_id=task.id,
            rationale=(
                "prioritized task coverage, balanced attempt ownership, then "
                "the weakest validated score, with relevant validated memory"
            ),
            retrieved_lesson_ids=tuple(lesson.id for lesson in lessons),
        )


def policy_for(name: str) -> SchedulerPolicy:
    normalized = name.lower().replace("-", "_")
    if normalized in {"managed"}:
        return ManagedPolicy()
    if normalized in {"round_robin", "naive"}:
        return RoundRobinPolicy()
    raise ValueError(f"unknown scheduler policy: {name}")

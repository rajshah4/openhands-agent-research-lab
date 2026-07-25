from __future__ import annotations

from typing import Any

from .domain import TaskSpec, ValidationResult


class GraphColoringValidator:
    """Validate graph color assignments and minimize distinct colors."""

    def validate(self, task: TaskSpec, candidate: dict[str, Any]) -> ValidationResult:
        assignments = candidate.get("assignments")
        if not isinstance(assignments, dict):
            return ValidationResult(False, None, ("candidate.assignments must be an object",))

        errors: list[str] = []
        normalized: dict[str, str] = {}
        for node in task.nodes:
            if node not in assignments:
                errors.append(f"missing assignment for node {node}")
                continue
            color = assignments[node]
            if isinstance(color, (dict, list)) or color is None:
                errors.append(f"invalid color for node {node}")
                continue
            normalized[node] = str(color)

        extra_nodes = set(str(key) for key in assignments) - set(task.nodes)
        if extra_nodes:
            errors.append(f"assignments contain unknown nodes: {', '.join(sorted(extra_nodes))}")

        for left, right in task.edges:
            if left in normalized and right in normalized and normalized[left] == normalized[right]:
                errors.append(f"edge {left}-{right} uses the same color")

        if errors:
            return ValidationResult(False, None, tuple(errors))
        score = float(len(set(normalized.values())))
        return ValidationResult(True, score, ())

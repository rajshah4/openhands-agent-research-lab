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


class SetCoverValidator:
    """Validate a selected family of sets and minimize the number selected."""

    def validate(self, task: TaskSpec, candidate: dict[str, Any]) -> ValidationResult:
        universe = {str(item) for item in task.payload.get("universe", [])}
        raw_sets = task.payload.get("sets")
        selected = candidate.get("selected_sets")
        if not universe or not isinstance(raw_sets, dict):
            return ValidationResult(False, None, ("task set-cover payload is invalid",))
        if not isinstance(selected, list):
            return ValidationResult(
                False, None, ("candidate.selected_sets must be an array",)
            )

        errors: list[str] = []
        selected_ids = [str(item) for item in selected]
        if len(set(selected_ids)) != len(selected_ids):
            errors.append("selected_sets contains duplicates")
        unknown = set(selected_ids) - {str(key) for key in raw_sets}
        if unknown:
            errors.append(f"unknown sets selected: {', '.join(sorted(unknown))}")
        covered: set[str] = set()
        for set_id in selected_ids:
            if set_id in raw_sets and isinstance(raw_sets[set_id], list):
                covered.update(str(item) for item in raw_sets[set_id])
        missing = universe - covered
        if missing:
            errors.append(f"uncovered elements: {', '.join(sorted(missing))}")
        if errors:
            return ValidationResult(False, None, tuple(errors))
        return ValidationResult(True, float(len(selected_ids)), ())


class BinPackingValidator:
    """Validate a bin assignment and minimize the number of fixed-capacity bins."""

    def validate(self, task: TaskSpec, candidate: dict[str, Any]) -> ValidationResult:
        raw_items = task.payload.get("items")
        capacity = task.payload.get("capacity")
        bins = candidate.get("bins")
        if not isinstance(raw_items, dict) or not isinstance(capacity, (int, float)):
            return ValidationResult(False, None, ("task bin-packing payload is invalid",))
        if not isinstance(bins, list) or not all(isinstance(bin_, list) for bin_ in bins):
            return ValidationResult(False, None, ("candidate.bins must be an array of arrays",))

        errors: list[str] = []
        known = {str(item) for item in raw_items}
        packed = [str(item) for bin_ in bins for item in bin_]
        packed_set = set(packed)
        missing = known - packed_set
        unknown = packed_set - known
        duplicates = sorted(item for item in packed_set if packed.count(item) > 1)
        if missing:
            errors.append(f"unpacked items: {', '.join(sorted(missing))}")
        if unknown:
            errors.append(f"unknown items packed: {', '.join(sorted(unknown))}")
        if duplicates:
            errors.append(f"items packed more than once: {', '.join(duplicates)}")
        for index, bin_ in enumerate(bins):
            weight = sum(
                float(raw_items[str(item)])
                for item in bin_
                if str(item) in raw_items
            )
            if weight > float(capacity):
                errors.append(
                    f"bin {index} exceeds capacity: {weight:g} > {float(capacity):g}"
                )
        if errors:
            return ValidationResult(False, None, tuple(errors))
        return ValidationResult(True, float(len(bins)), ())


class DeterministicValidator:
    """Dispatch validation by benchmark family without trusting worker claims."""

    def __init__(self) -> None:
        self.validators = {
            "graph-coloring": GraphColoringValidator(),
            "set-cover": SetCoverValidator(),
            "bin-packing": BinPackingValidator(),
        }

    def validate(self, task: TaskSpec, candidate: dict[str, Any]) -> ValidationResult:
        validator = self.validators.get(task.family)
        if validator is None:
            return ValidationResult(
                False,
                None,
                (f"unsupported benchmark family: {task.family}",),
            )
        return validator.validate(task, candidate)

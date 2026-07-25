import unittest

from research_lab.benchmark import (
    BinPackingValidator,
    DeterministicValidator,
    GraphColoringValidator,
    SetCoverValidator,
)
from research_lab.domain import TaskSpec


TASK = TaskSpec(
    id="triangle",
    family="graph-coloring",
    description="triangle",
    tags=("graph-coloring",),
    nodes=("0", "1", "2"),
    edges=(("0", "1"), ("1", "2"), ("2", "0")),
)


class GraphColoringValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = GraphColoringValidator()

    def test_valid_candidate_scores_distinct_colors(self) -> None:
        result = self.validator.validate(
            TASK,
            {"assignments": {"0": 0, "1": 1, "2": 2}},
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.score, 3.0)

    def test_rejects_conflicting_edge(self) -> None:
        result = self.validator.validate(
            TASK,
            {"assignments": {"0": 0, "1": 0, "2": 1}},
        )
        self.assertFalse(result.valid)
        self.assertIn("edge 0-1 uses the same color", result.errors)

    def test_rejects_missing_and_extra_nodes(self) -> None:
        result = self.validator.validate(
            TASK,
            {"assignments": {"0": 0, "1": 1, "extra": 2}},
        )
        self.assertFalse(result.valid)
        self.assertTrue(any("missing assignment" in error for error in result.errors))
        self.assertTrue(any("unknown nodes" in error for error in result.errors))


class SetCoverValidatorTests(unittest.TestCase):
    def test_scores_valid_cover_and_rejects_missing_elements(self) -> None:
        task = TaskSpec(
            id="cover",
            family="set-cover",
            description="cover",
            tags=("set-cover",),
            target_score=2,
            payload={
                "universe": ["a", "b", "c"],
                "sets": {"left": ["a", "b"], "right": ["c"]},
            },
        )
        validator = SetCoverValidator()
        self.assertEqual(
            validator.validate(task, {"selected_sets": ["left", "right"]}).score,
            2,
        )
        result = validator.validate(task, {"selected_sets": ["left"]})
        self.assertFalse(result.valid)
        self.assertIn("uncovered elements: c", result.errors)


class BinPackingValidatorTests(unittest.TestCase):
    def test_scores_valid_bins_and_rejects_overweight_bin(self) -> None:
        task = TaskSpec(
            id="packing",
            family="bin-packing",
            description="pack",
            tags=("bin-packing",),
            target_score=2,
            payload={"capacity": 10, "items": {"a": 6, "b": 4, "c": 5}},
        )
        validator = BinPackingValidator()
        self.assertEqual(
            validator.validate(task, {"bins": [["a", "b"], ["c"]]}).score,
            2,
        )
        result = validator.validate(task, {"bins": [["a", "c"], ["b"]]})
        self.assertFalse(result.valid)
        self.assertTrue(any("exceeds capacity" in error for error in result.errors))

    def test_registry_rejects_unsupported_family(self) -> None:
        task = TaskSpec(
            id="unknown",
            family="unknown",
            description="unknown",
            tags=(),
        )
        result = DeterministicValidator().validate(task, {})
        self.assertFalse(result.valid)
        self.assertIn("unsupported benchmark family", result.errors[0])


if __name__ == "__main__":
    unittest.main()

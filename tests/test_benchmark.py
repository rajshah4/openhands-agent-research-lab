import unittest

from research_lab.benchmark import GraphColoringValidator
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


if __name__ == "__main__":
    unittest.main()

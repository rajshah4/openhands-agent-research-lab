import tempfile
import unittest
from pathlib import Path

from research_lab.comparison import MatchedComparisonRunner
from research_lab.domain import CampaignSpec
from research_lab.store import FileResearchStore
from research_lab.workers import LocalHeuristicWorker


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MatchedComparisonTests(unittest.TestCase):
    def test_isolated_arms_measure_validated_memory_effect(self) -> None:
        campaign = CampaignSpec.from_path(
            PROJECT_ROOT / "examples" / "graph-coloring-campaign.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            comparison_id, comparison, report = MatchedComparisonRunner(
                root=root,
                worker=LocalHeuristicWorker(),
            ).run(campaign)

            naive = comparison["arms"]["naive"]["metrics"]
            managed = comparison["arms"]["managed"]["metrics"]
            self.assertEqual(naive["problems_solved"], managed["problems_solved"])
            self.assertGreater(
                managed["normalized_solution_quality"],
                naive["normalized_solution_quality"],
            )
            self.assertGreater(managed["quality_auc"], naive["quality_auc"])

            comparison_path = root / "comparisons" / comparison_id
            self.assertTrue((comparison_path / "comparison.json").exists())
            self.assertTrue((comparison_path / "report.md").exists())
            self.assertIn("stores were isolated", report)

            naive_store = FileResearchStore(comparison_path / "arms" / "naive")
            managed_store = FileResearchStore(comparison_path / "arms" / "managed")
            naive_attempts = naive_store.list_attempts(
                comparison["arms"]["naive"]["run_id"]
            )
            managed_attempts = managed_store.list_attempts(
                comparison["arms"]["managed"]["run_id"]
            )
            self.assertFalse(
                any(attempt["retrieved_lesson_ids"] for attempt in naive_attempts)
            )
            self.assertTrue(
                any(attempt["retrieved_lesson_ids"] for attempt in managed_attempts)
            )


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from research_lab.domain import CampaignSpec
from research_lab.runner import CampaignRunner
from research_lab.scheduler import ManagedPolicy
from research_lab.store import FileResearchStore
from research_lab.workers import LocalHeuristicWorker


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CampaignRunnerTests(unittest.TestCase):
    def test_offline_campaign_records_attempts_lessons_and_report(self) -> None:
        campaign = CampaignSpec.from_path(
            PROJECT_ROOT / "examples" / "graph-coloring-campaign.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            store = FileResearchStore(Path(directory))
            runner = CampaignRunner(
                store=store,
                worker=LocalHeuristicWorker(),
                scheduler=ManagedPolicy(),
            )
            run_id, report = runner.run(campaign)
            attempts = store.list_attempts(run_id)
            self.assertEqual(len(attempts), campaign.attempt_budget)
            self.assertTrue(all(item["validation"]["valid"] for item in attempts))
            self.assertTrue(any(item["promoted_lesson_id"] for item in attempts))
            self.assertTrue(any(item["retrieved_lesson_ids"] for item in attempts[1:]))
            self.assertIn("Duplicate candidates:", report)
            self.assertTrue((Path(directory) / "runs" / run_id / "report.md").exists())
            lifecycle_files = list(
                (Path(directory) / "runs" / run_id / "lifecycle").glob("*/*.json")
            )
            self.assertGreaterEqual(len(lifecycle_files), campaign.attempt_budget * 4)


if __name__ == "__main__":
    unittest.main()

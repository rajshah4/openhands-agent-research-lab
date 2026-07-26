import tempfile
import unittest
from pathlib import Path

from research_lab.domain import CampaignSpec
from research_lab.scheduler import ManagedPolicy
from research_lab.store import FileResearchStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ManagedPolicyTests(unittest.TestCase):
    def test_balances_attempt_ownership_before_revisiting_weaker_tasks(self) -> None:
        campaign = CampaignSpec.from_path(
            PROJECT_ROOT / "examples" / "graph-coloring-campaign.json"
        )
        first, second, third = campaign.tasks
        attempts = [
            {
                "task_id": first.id,
                "validation": {"valid": True, "score": 99},
            },
            {
                "task_id": second.id,
                "validation": {"valid": True, "score": 1},
            },
            {
                "task_id": second.id,
                "validation": {"valid": True, "score": 1},
            },
            {
                "task_id": third.id,
                "validation": {"valid": True, "score": 1},
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            selected, decision = ManagedPolicy().choose(
                campaign.tasks,
                attempts,
                FileResearchStore(Path(directory)),
            )
        self.assertEqual(selected.id, first.id)
        self.assertIn("balanced attempt ownership", decision.rationale)


if __name__ == "__main__":
    unittest.main()

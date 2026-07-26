import unittest
from pathlib import Path

from research_lab.cli import _campaign, build_parser


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CampaignSelectionTests(unittest.TestCase):
    def test_task_id_restricts_campaign_without_reordering(self) -> None:
        args = build_parser().parse_args(
            [
                "preflight",
                "--campaign",
                str(PROJECT_ROOT / "examples" / "hard-transfer-live.json"),
                "--task-id",
                "cover-02-bridges",
                "--task-id",
                "color-01-crown-12",
            ]
        )
        campaign = _campaign(args)
        self.assertEqual(
            [task.id for task in campaign.tasks],
            ["color-01-crown-12", "cover-02-bridges"],
        )

    def test_unknown_task_id_is_rejected(self) -> None:
        args = build_parser().parse_args(
            [
                "preflight",
                "--campaign",
                str(PROJECT_ROOT / "examples" / "hard-transfer-live.json"),
                "--task-id",
                "not-a-task",
            ]
        )
        with self.assertRaisesRegex(ValueError, "not-a-task"):
            _campaign(args)


if __name__ == "__main__":
    unittest.main()

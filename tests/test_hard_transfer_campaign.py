import unittest
from pathlib import Path

from research_lab.benchmark import DeterministicValidator
from research_lab.domain import CampaignSpec


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class HardTransferCampaignTests(unittest.TestCase):
    def test_known_witnesses_reach_every_target(self) -> None:
        campaign = CampaignSpec.from_path(
            PROJECT_ROOT / "examples" / "hard-transfer-live.json"
        )
        self.assertEqual(len(campaign.tasks), 6)
        self.assertEqual(
            {task.family for task in campaign.tasks},
            {"graph-coloring", "set-cover", "bin-packing"},
        )
        witnesses = {
            "color-01-crown-12": {
                "assignments": {
                    **{f"p{index}": 0 for index in range(1, 7)},
                    **{f"q{index}": 1 for index in range(1, 7)},
                }
            },
            "color-02-mycielski-11": {
                "assignments": {
                    "v0": 0, "v1": 1, "v2": 0, "v3": 1, "v4": 2,
                    "u0": 0, "u1": 1, "u2": 0, "u3": 1, "u4": 2,
                    "w": 3,
                }
            },
            "cover-01-constellations": {
                "selected_sets": ["atlas", "beacon", "cipher"]
            },
            "cover-02-bridges": {
                "selected_sets": ["north", "east", "south", "west"]
            },
            "pack-01-pairs-12": {
                "bins": [
                    ["amber", "dune"], ["gale", "jade"],
                    ["elm", "birch"], ["kelp", "heath"],
                    ["coral", "frost"], ["iris", "lumen"],
                ]
            },
            "pack-02-pairs-16": {
                "bins": [
                    ["aqua", "flint"], ["ivory", "navy"],
                    ["ember", "brass"], ["moss", "juniper"],
                    ["cedar", "honey"], ["khaki", "pearl"],
                    ["grove", "denim"], ["ochre", "linen"],
                ]
            },
        }
        validator = DeterministicValidator()
        for task in campaign.tasks:
            with self.subTest(task=task.id):
                result = validator.validate(task, witnesses[task.id])
                self.assertTrue(result.valid, result.errors)
                self.assertEqual(result.score, task.target_score)


if __name__ == "__main__":
    unittest.main()

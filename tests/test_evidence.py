import json
import tempfile
import unittest
from pathlib import Path

from research_lab.comparison import MatchedComparisonRunner
from research_lab.domain import CampaignSpec
from research_lab.evidence import export_comparison_evidence
from research_lab.workers import LocalHeuristicWorker


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class EvidenceExportTests(unittest.TestCase):
    def test_exports_structured_attempts_without_worker_content(self) -> None:
        campaign = CampaignSpec.from_path(
            PROJECT_ROOT / "examples" / "graph-coloring-campaign.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            comparison_id, _, _ = MatchedComparisonRunner(
                root=root,
                worker=LocalHeuristicWorker(),
            ).run(campaign)
            comparison_path = (
                root / "comparisons" / comparison_id / "comparison.json"
            )
            output = root / "evidence.json"
            evidence = export_comparison_evidence(comparison_path, output)
            persisted = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(persisted["schema_version"], 1)
        self.assertEqual(
            sum(len(arm["attempts"]) for arm in evidence["arms"].values()),
            campaign.attempt_budget * 2,
        )
        serialized = json.dumps(persisted)
        self.assertNotIn("final_text", serialized)
        self.assertIn("candidate_hash", serialized)
        for arm in persisted["arms"].values():
            for attempt in arm["attempts"]:
                self.assertNotIn("candidate", attempt)

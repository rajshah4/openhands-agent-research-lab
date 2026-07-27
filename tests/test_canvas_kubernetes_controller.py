from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "experiments"
    / "agent-canvas-kubernetes"
    / "controller"
    / "controller_tick.py"
)
SPEC = importlib.util.spec_from_file_location("canvas_controller_tick", MODULE_PATH)
assert SPEC and SPEC.loader
CONTROLLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROLLER)


class CanvasKubernetesControllerTests(unittest.TestCase):
    def write_run(
        self,
        store: Path,
        *,
        run_id: str,
        attempts: int,
        budget: int = 3,
    ) -> None:
        run = store / "runs" / run_id
        (run / "attempts").mkdir(parents=True)
        (run / "manifest.json").write_text(
            json.dumps(
                {
                    "id": run_id,
                    "campaign": {
                        "id": "test-campaign",
                        "attempt_budget": budget,
                    },
                }
            )
        )
        for sequence in range(1, attempts + 1):
            (run / "attempts" / f"attempt-{sequence:04d}.json").write_text("{}")

    def test_matching_runs_reports_resumable_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = Path(temporary)
            self.write_run(store, run_id="test-campaign-run", attempts=2)

            self.assertEqual(
                CONTROLLER.matching_runs(store, "test-campaign"),
                [
                    {
                        "run_id": "test-campaign-run",
                        "attempts": 2,
                        "attempt_budget": 3,
                    }
                ],
            )

    def test_matching_runs_ignores_other_campaigns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = Path(temporary)
            self.write_run(store, run_id="test-campaign-run", attempts=3)

            self.assertEqual(CONTROLLER.matching_runs(store, "other"), [])

    def test_atomic_json_replaces_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status = Path(temporary) / "controller-status.json"

            CONTROLLER.atomic_json(status, {"state": "waiting"})
            CONTROLLER.atomic_json(status, {"state": "complete"})

            self.assertEqual(
                json.loads(status.read_text()),
                {"state": "complete"},
            )


if __name__ == "__main__":
    unittest.main()

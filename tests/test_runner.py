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

    def test_runner_reads_attempt_ledger_once(self) -> None:
        campaign = CampaignSpec.from_path(
            PROJECT_ROOT / "examples" / "graph-coloring-campaign.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            store = FileResearchStore(Path(directory))
            list_calls = 0
            original = store.list_attempts

            def counted(run_id: str) -> list[dict[str, object]]:
                nonlocal list_calls
                list_calls += 1
                return original(run_id)

            store.list_attempts = counted  # type: ignore[method-assign]
            runner = CampaignRunner(
                store=store,
                worker=LocalHeuristicWorker(),
                scheduler=ManagedPolicy(),
            )
            runner.run(campaign)
            self.assertEqual(list_calls, 1)

    def test_resume_reuses_incomplete_attempt_and_skips_completed_work(self) -> None:
        campaign = CampaignSpec.from_path(
            PROJECT_ROOT / "examples" / "graph-coloring-campaign.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            store = FileResearchStore(Path(directory))
            scheduler = ManagedPolicy()
            run_id = "resume-test"
            store.create_run(
                run_id,
                {
                    "schema_version": 1,
                    "id": run_id,
                    "campaign": campaign.to_dict(),
                    "scheduler": {
                        "name": scheduler.name,
                        "version": scheduler.version,
                    },
                    "created_at": "2026-07-26T00:00:00+00:00",
                    "storage_contract": "single-controller-file-lock",
                },
            )
            task, decision = scheduler.choose(campaign.tasks, [], store)
            attempt_id = "attempt-0001-interrupted"
            store.append_lifecycle_event(
                run_id,
                attempt_id,
                {
                    "schema_version": 1,
                    "id": "0001-attempt_selected",
                    "run_id": run_id,
                    "attempt_id": attempt_id,
                    "kind": "attempt_selected",
                    "recorded_at": "2026-07-26T00:00:01+00:00",
                    "payload": {
                        "sequence": 1,
                        "task_id": task.id,
                        "scheduler_decision": decision.to_dict(),
                    },
                },
            )

            runner = CampaignRunner(
                store=store,
                worker=LocalHeuristicWorker(),
                scheduler=scheduler,
            )
            resumed_run_id, _ = runner.run(
                campaign,
                resume_run_id=run_id,
            )
            attempts = store.list_attempts(run_id)
            self.assertEqual(resumed_run_id, run_id)
            self.assertEqual(len(attempts), campaign.attempt_budget)
            self.assertEqual(attempts[0]["id"], attempt_id)
            self.assertEqual(
                {int(attempt["sequence"]) for attempt in attempts},
                set(range(1, campaign.attempt_budget + 1)),
            )
            recovered_events = store.list_lifecycle_events(run_id, attempt_id)
            self.assertTrue(
                any(
                    event["kind"] == "attempt_recovery_started"
                    for event in recovered_events
                )
            )


if __name__ == "__main__":
    unittest.main()

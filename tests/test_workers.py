import json
import unittest

from research_lab.domain import CampaignSpec, TaskSpec
from research_lab.openhands import OpenHandsCapacityError
from research_lab.workers import OpenHandsWorker, render_worker_prompt


class FakeOpenHandsClient:
    def __init__(self) -> None:
        self.paused = []
        self.starts = 0
        self.active = 1

    def capacity_snapshot(self, *, runtime_limit, launch_lock_at):
        return {
            "scope": "authenticated-user-visible-sandboxes",
            "active": self.active,
            "runtime_limit": runtime_limit,
            "launch_lock_at": launch_lock_at,
            "launch_allowed": self.active < launch_lock_at,
        }

    def start_conversation(self, **kwargs):
        self.starts += 1
        return {"id": "start-1"}

    def poll_start_task(self, *args, **kwargs):
        return {
            "app_conversation_id": "conversation-1",
            "sandbox_id": "sandbox-1",
        }

    def wait_for_terminal(self, *args, **kwargs):
        return (
            {
                "execution_status": "finished",
                "sandbox_status": "RUNNING",
                "sandbox_id": "sandbox-1",
            },
            [],
            False,
        )

    def final_response(self, *args, **kwargs):
        return ('{"status":"done"}', [])

    def pause_sandbox(self, sandbox_id, **kwargs):
        self.paused.append(sandbox_id)
        return {"id": sandbox_id, "status": "PAUSED"}

    def conversation_url(self, conversation_id):
        return f"https://example.test/conversations/{conversation_id}"


class OpenHandsWorkerTests(unittest.TestCase):
    def test_default_campaign_serialization_remains_backward_compatible(self) -> None:
        campaign = CampaignSpec(
            id="campaign-1",
            name="Campaign",
            policy="managed",
            attempt_budget=1,
            repository=None,
            branch=None,
            model=None,
            tasks=(),
        )

        self.assertNotIn("research_protocol", campaign.to_dict())

    def test_pauses_sandbox_after_final_response(self) -> None:
        client = FakeOpenHandsClient()
        lifecycle = []
        worker = OpenHandsWorker(client, poll_seconds=1)
        campaign = CampaignSpec(
            id="campaign-1",
            name="Campaign",
            policy="managed",
            attempt_budget=1,
            repository="owner/repo",
            branch="main",
            model=None,
            tasks=(),
        )
        task = TaskSpec(
            id="task-1",
            family="graph-coloring",
            description="test",
            tags=("graph-coloring",),
            nodes=("0",),
            edges=(),
            target_score=1,
        )

        worker.execute(
            campaign=campaign,
            task=task,
            run_id="run-1",
            attempt_id="attempt-1",
            lessons=[],
            on_lifecycle=lambda kind, payload: lifecycle.append((kind, payload)),
        )

        self.assertEqual(client.paused, ["sandbox-1"])
        self.assertEqual(client.starts, 1)
        self.assertEqual(lifecycle[0][0], "capacity_checked")
        self.assertIn("sandbox_pause_requested", [kind for kind, _ in lifecycle])
        self.assertIn("sandbox_paused", [kind for kind, _ in lifecycle])

    def test_refuses_launch_when_capacity_gate_is_closed(self) -> None:
        client = FakeOpenHandsClient()
        client.active = 7
        lifecycle = []
        worker = OpenHandsWorker(client, launch_lock_at=7)
        campaign = CampaignSpec(
            id="campaign-1",
            name="Campaign",
            policy="managed",
            attempt_budget=1,
            repository=None,
            branch=None,
            model=None,
            tasks=(),
        )
        task = TaskSpec(
            id="task-1",
            family="graph-coloring",
            description="test",
            tags=("graph-coloring",),
            nodes=("0",),
            edges=(),
            target_score=1,
        )

        with self.assertRaises(OpenHandsCapacityError):
            worker.execute(
                campaign=campaign,
                task=task,
                run_id="run-1",
                attempt_id="attempt-1",
                lessons=[],
                on_lifecycle=lambda kind, payload: lifecycle.append((kind, payload)),
            )

        self.assertEqual(client.starts, 0)
        self.assertEqual([kind for kind, _ in lifecycle], ["capacity_checked"])

    def test_records_failed_start_sandbox_for_cleanup(self) -> None:
        client = FakeOpenHandsClient()
        client.poll_start_task = lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("start failed")
        )
        client.get_start_task = lambda task_id: {
            "id": task_id,
            "status": "ERROR",
            "detail": "provider unavailable",
            "sandbox_id": "sandbox-failed",
        }
        lifecycle = []
        worker = OpenHandsWorker(client, poll_seconds=1)
        campaign = CampaignSpec(
            id="campaign-1",
            name="Campaign",
            policy="managed",
            attempt_budget=1,
            repository=None,
            branch=None,
            model=None,
            tasks=(),
        )
        task = TaskSpec(
            id="task-1",
            family="graph-coloring",
            description="test",
            tags=("graph-coloring",),
            nodes=("0",),
            edges=(),
            target_score=1,
        )

        with self.assertRaisesRegex(RuntimeError, "start failed"):
            worker.execute(
                campaign=campaign,
                task=task,
                run_id="run-1",
                attempt_id="attempt-1",
                lessons=[],
                on_lifecycle=lambda kind, payload: lifecycle.append((kind, payload)),
            )

        failed = [payload for kind, payload in lifecycle if kind == "conversation_start_failed"]
        self.assertEqual(failed[0]["sandbox_id"], "sandbox-failed")
        self.assertEqual(failed[0]["detail"], "provider unavailable")

    def test_bin_packing_contract_example_uses_exact_task_item_ids(self) -> None:
        campaign = CampaignSpec(
            id="campaign-1",
            name="Campaign",
            policy="managed",
            attempt_budget=1,
            repository=None,
            branch=None,
            model=None,
            tasks=(),
        )
        task = TaskSpec(
            id="pack",
            family="bin-packing",
            description="pack",
            tags=("bin-packing",),
            payload={"capacity": 10, "items": {"a": 6, "b": 4}},
        )
        prompt = render_worker_prompt(
            campaign=campaign,
            task=task,
            run_id="run-1",
            attempt_id="attempt-1",
            lessons=[],
        )
        self.assertIn('"bins": [', prompt)
        self.assertIn('"a"', prompt)
        self.assertNotIn('"item-a"', prompt)
        self.assertIn("Never add a", prompt)

    def test_endurance_protocol_requires_multi_stage_tool_work(self) -> None:
        campaign = CampaignSpec(
            id="campaign-1",
            name="Campaign",
            policy="managed",
            attempt_budget=1,
            repository="owner/repo",
            branch="main",
            model=None,
            tasks=(),
            research_protocol="endurance-v1",
        )
        task = TaskSpec(
            id="pack",
            family="bin-packing",
            description="pack",
            tags=("bin-packing",),
            payload={"capacity": 10, "items": {"a": 6, "b": 4}},
        )

        prompt = render_worker_prompt(
            campaign=campaign,
            task=task,
            run_id="run-1",
            attempt_id="attempt-1",
            lessons=[],
        )

        self.assertIn("Endurance research protocol", prompt)
        self.assertIn("at least three solution approaches", prompt)
        self.assertIn("12 seeded orderings or perturbations", prompt)
        self.assertIn("complete attempt within twenty minutes", prompt)
        self.assertIn("experiment/worker-artifact/attempt-1", prompt)
        self.assertIn(
            ".research-artifacts/run-1/attempt-1.json",
            prompt,
        )

    def test_endurance_worker_prefers_git_artifact(self) -> None:
        client = FakeOpenHandsClient()
        lifecycle = []
        artifact = json.dumps(
            {
                "status": "done",
                "candidate": {"assignments": {"0": 0}},
                "lesson": None,
                "summary": ["artifact"],
                "next_gate": "validate",
            }
        )
        worker = OpenHandsWorker(
            client,
            poll_seconds=1,
            artifact_reader=lambda branch, path: artifact,
        )
        campaign = CampaignSpec(
            id="campaign-1",
            name="Campaign",
            policy="managed",
            attempt_budget=1,
            repository="owner/repository",
            branch="main",
            model=None,
            tasks=(),
            research_protocol="endurance-v1",
        )
        task = TaskSpec(
            id="task-1",
            family="graph-coloring",
            description="test",
            tags=("graph-coloring",),
            nodes=("0",),
            edges=(),
            target_score=1,
        )

        execution = worker.execute(
            campaign=campaign,
            task=task,
            run_id="run-1",
            attempt_id="attempt-1",
            lessons=[],
            on_lifecycle=lambda kind, payload: lifecycle.append((kind, payload)),
        )

        self.assertEqual(execution.final_text, artifact)
        self.assertEqual(
            execution.metadata["final_response_source"],
            "git_artifact",
        )
        self.assertIn("worker_artifact_ready", [kind for kind, _ in lifecycle])

    def test_controller_enforces_controlled_dwell_before_cleanup(self) -> None:
        client = FakeOpenHandsClient()
        lifecycle = []
        delays = []
        times = iter((100.0, 220.0))
        worker = OpenHandsWorker(
            client,
            poll_seconds=1,
            sleeper=delays.append,
            monotonic=lambda: next(times),
        )
        campaign = CampaignSpec(
            id="campaign-1",
            name="Campaign",
            policy="managed",
            attempt_budget=1,
            repository=None,
            branch=None,
            model=None,
            tasks=(),
            controlled_dwell_seconds=600,
        )
        task = TaskSpec(
            id="task-1",
            family="graph-coloring",
            description="test",
            tags=("graph-coloring",),
            nodes=("0",),
            edges=(),
            target_score=1,
        )

        worker.execute(
            campaign=campaign,
            task=task,
            run_id="run-1",
            attempt_id="attempt-1",
            lessons=[],
            on_lifecycle=lambda kind, payload: lifecycle.append((kind, payload)),
        )

        self.assertEqual(delays, [480.0])
        kinds = [kind for kind, _ in lifecycle]
        self.assertLess(
            kinds.index("controlled_dwell_completed"),
            kinds.index("sandbox_pause_requested"),
        )

    def test_recovery_reuses_completed_dwell(self) -> None:
        client = FakeOpenHandsClient()
        lifecycle = []
        delays = []
        worker = OpenHandsWorker(
            client,
            poll_seconds=1,
            sleeper=delays.append,
            artifact_reader=lambda branch, path: json.dumps(
                {
                    "status": "done",
                    "candidate": {"assignments": {"0": 0}},
                    "lesson": None,
                    "summary": ["artifact"],
                    "next_gate": "validate",
                }
            ),
        )
        campaign = CampaignSpec(
            id="campaign-1",
            name="Campaign",
            policy="managed",
            attempt_budget=1,
            repository="owner/repository",
            branch="main",
            model=None,
            tasks=(),
            research_protocol="endurance-v1",
            controlled_dwell_seconds=600,
        )
        task = TaskSpec(
            id="task-1",
            family="graph-coloring",
            description="test",
            tags=("graph-coloring",),
            nodes=("0",),
            edges=(),
            target_score=1,
        )

        worker.recover(
            campaign=campaign,
            task=task,
            run_id="run-1",
            attempt_id="attempt-1",
            lessons=[],
            lifecycle_events=[
                {
                    "kind": "start_task_created",
                    "payload": {"start_task_id": "start-1"},
                },
                {"kind": "sandbox_pause_requested", "payload": {}},
            ],
            on_lifecycle=lambda kind, payload: lifecycle.append((kind, payload)),
        )

        self.assertEqual(delays, [])
        self.assertIn("controlled_dwell_reused", [kind for kind, _ in lifecycle])


if __name__ == "__main__":
    unittest.main()

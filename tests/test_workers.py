import unittest

from research_lab.domain import CampaignSpec, TaskSpec
from research_lab.workers import OpenHandsWorker


class FakeOpenHandsClient:
    def __init__(self) -> None:
        self.paused = []

    def start_conversation(self, **kwargs):
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
        self.assertIn("sandbox_pause_requested", [kind for kind, _ in lifecycle])
        self.assertIn("sandbox_paused", [kind for kind, _ in lifecycle])


if __name__ == "__main__":
    unittest.main()

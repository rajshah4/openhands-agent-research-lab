import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from research_lab.canvas import CanvasClient, CanvasWorker
from research_lab.domain import CampaignSpec, TaskSpec
from research_lab.openhands import OpenHandsAPIError, request_json


class CanvasClientTests(unittest.TestCase):
    def test_preflight_returns_capabilities_without_settings_payload(self) -> None:
        def requester(method, url, headers, body=None, timeout=60):
            if url.endswith("/health"):
                return {"status": "ok"}
            if url.endswith("/ready"):
                return {"status": "ready"}
            if url.endswith("/api/settings"):
                return {
                    "llm_api_key_is_set": True,
                    "agent_settings": {
                        "llm": {
                            "model": "provider/model",
                            "api_key": "do-not-return",
                        }
                    },
                }
            if url.endswith("/api/profiles"):
                return {
                    "profiles": [{"name": "test-profile"}],
                    "active_profile": "test-profile",
                }
            raise AssertionError(url)

        client = CanvasClient(
            "http://canvas.test",
            "not-logged",
            requester=requester,
        )
        self.assertEqual(
            client.preflight(),
            {
                "health": "ok",
                "ready": "ready",
                "llm_api_key_is_set": True,
                "model": "provider/model",
                "active_profile": "test-profile",
            },
        )

    def test_start_conversation_uses_local_workspace_and_bounded_run(self) -> None:
        captured = {}

        def requester(method, url, headers, body=None, timeout=60):
            captured.update(
                {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "body": body,
                }
            )
            return {
                "id": "conversation-1",
                "secret_registry": {"api_key": "do-not-persist"},
            }

        client = CanvasClient(
            "http://canvas.test/",
            "session-key",
            requester=requester,
        )
        record = client.start_conversation(
            prompt="bounded task",
            workspace=Path("/tmp/attempt-1"),
            max_iterations=12,
            tags={"attempt": "attempt-1"},
            agent_settings={
                "agent_kind": "Agent",
                "llm": {"model": "provider/model"},
            },
        )
        self.assertEqual(record, {"id": "conversation-1", "secret_registry": {}})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "http://canvas.test/api/conversations")
        self.assertEqual(
            captured["headers"]["X-Session-API-Key"],
            "session-key",
        )
        payload = captured["body"]
        self.assertEqual(payload["workspace"]["kind"], "LocalWorkspace")
        self.assertEqual(
            payload["workspace"]["working_dir"],
            str(Path("/tmp/attempt-1").resolve()),
        )
        self.assertEqual(payload["confirmation_policy"], {"kind": "NeverConfirm"})
        self.assertFalse(payload["initial_message"]["run"])
        self.assertEqual(payload["max_iterations"], 12)
        self.assertFalse(payload["autotitle"])
        self.assertEqual(
            payload["agent_settings"],
            {
                "agent_kind": "Agent",
                "llm": {"model": "provider/model"},
            },
        )
        self.assertTrue(payload["secrets_encrypted"])

    def test_agent_settings_remove_unrelated_shared_backend_capabilities(self) -> None:
        original = {
            "agent_kind": "openhands",
            "llm": {"model": "provider/model"},
            "tools": [],
            "mcp_config": {"slack": {"command": "npx"}},
            "enable_sub_agents": True,
            "enable_switch_llm_tool": True,
            "tool_concurrency_limit": 8,
        }

        def requester(method, url, headers, body=None, timeout=60):
            self.assertTrue(url.endswith("/api/settings"))
            self.assertEqual(headers["X-Expose-Secrets"], "encrypted")
            return {"agent_settings": original}

        client = CanvasClient(
            "http://canvas.test",
            "not-logged",
            requester=requester,
        )
        settings = client.agent_settings()
        self.assertIsNone(settings["tools"])
        self.assertEqual(settings["mcp_config"], {})
        self.assertFalse(settings["enable_sub_agents"])
        self.assertFalse(settings["enable_switch_llm_tool"])
        self.assertEqual(settings["tool_concurrency_limit"], 1)
        self.assertEqual(
            original["mcp_config"],
            {"slack": {"command": "npx"}},
        )

    def test_fetch_events_paginates_and_sanitizes(self) -> None:
        def requester(method, url, headers, body=None, timeout=60):
            if "page_id=page-2" in url:
                return {
                    "items": [{"kind": "FinishAction"}],
                    "next_page_id": None,
                }
            return {
                "items": [
                    {
                        "kind": "MessageEvent",
                        "session_api_key": "do-not-persist",
                    }
                ],
                "next_page_id": "page-2",
            }

        client = CanvasClient(
            "http://canvas.test",
            "not-logged",
            requester=requester,
        )
        self.assertEqual(
            client.fetch_events("conversation-1"),
            [{"kind": "MessageEvent"}, {"kind": "FinishAction"}],
        )

    def test_capacity_snapshot_paginates_and_counts_running_only(self) -> None:
        def requester(method, url, headers, body=None, timeout=60):
            if "page_id=page-2" in url:
                return {
                    "items": [
                        {"id": "conversation-3", "execution_status": "running"},
                        {"id": "conversation-4", "execution_status": "error"},
                    ],
                    "next_page_id": None,
                }
            return {
                "items": [
                    {"id": "conversation-1", "execution_status": "running"},
                    {"id": "conversation-2", "execution_status": "idle"},
                ],
                "next_page_id": "page-2",
            }

        client = CanvasClient(
            "http://canvas.test",
            "not-logged",
            requester=requester,
        )
        snapshot = client.capacity_snapshot(launch_lock_at=2)
        self.assertEqual(snapshot["active"], 2)
        self.assertEqual(snapshot["observed_conversations"], 4)
        self.assertFalse(snapshot["launch_allowed"])
        self.assertEqual(
            snapshot["status_counts"],
            {"error": 1, "idle": 1, "running": 2},
        )

    def test_wait_for_terminal_and_final_response_grace(self) -> None:
        statuses = iter(["running", "finished"])
        final_responses = iter(["", '{"status":"done"}'])

        def requester(method, url, headers, body=None, timeout=60):
            if url.endswith("/events/search?sort_order=TIMESTAMP&limit=100"):
                return {"items": [], "next_page_id": None}
            if url.endswith("/agent_final_response"):
                return {"response": next(final_responses)}
            if "/api/conversations/" in url:
                return {"id": "conversation-1", "execution_status": next(statuses)}
            raise AssertionError(url)

        client = CanvasClient(
            "http://canvas.test",
            "not-logged",
            requester=requester,
            sleeper=lambda _: None,
            monotonic=lambda: 0,
        )
        record, events = client.wait_for_terminal("conversation-1")
        self.assertEqual(record["execution_status"], "finished")
        self.assertEqual(events, [])
        self.assertEqual(
            client.final_response("conversation-1", retries=1),
            '{"status":"done"}',
        )

    def test_run_treats_already_running_conflict_as_success(self) -> None:
        def requester(method, url, headers, body=None, timeout=60):
            raise OpenHandsAPIError(
                "POST /api/conversations/conversation-1/run -> HTTP 409: "
                '{"detail":"Conversation already running."}'
            )

        client = CanvasClient(
            "http://canvas.test",
            "not-logged",
            requester=requester,
        )
        client.run_conversation("conversation-1")

    def test_http_validation_error_does_not_echo_prompt_or_secret(self) -> None:
        response = {
            "detail": [
                {
                    "input": {
                        "initial_message": {
                            "content": [{"type": "text", "text": "private task"}]
                        },
                        "api_key": "private credential",
                    }
                }
            ]
        }
        error = urllib.error.HTTPError(
            "http://canvas.test/api/conversations",
            422,
            "Unprocessable Entity",
            {},
            io.BytesIO(json.dumps(response).encode("utf-8")),
        )
        with patch(
            "research_lab.openhands.urllib.request.urlopen",
            side_effect=error,
        ):
            with self.assertRaises(OpenHandsAPIError) as raised:
                request_json(
                    "POST",
                    "http://canvas.test/api/conversations",
                    {"Content-Type": "application/json"},
                    body={"prompt": "private task"},
                )
        message = str(raised.exception)
        self.assertNotIn("private task", message)
        self.assertNotIn("private credential", message)
        self.assertIn("<redacted-content>", message)


class FakeCanvasClient:
    def __init__(self):
        self.workspace = None
        self.resolve_workspace_locally = None
        self.run_calls = 0

    def preflight(self):
        return {
            "health": "ok",
            "ready": "ready",
            "llm_api_key_is_set": True,
            "model": "provider/model",
            "active_profile": "test-profile",
        }

    def start_conversation(self, **kwargs):
        self.workspace = kwargs["workspace"]
        self.resolve_workspace_locally = kwargs["resolve_workspace_locally"]
        self.settings = kwargs["agent_settings"]
        return {
            "id": "conversation-1",
            "execution_status": "running",
        }

    def capacity_snapshot(self, *, launch_lock_at):
        return {
            "scope": "shared-canvas-conversations",
            "active": 0,
            "launch_lock_at": launch_lock_at,
            "launch_allowed": True,
            "status_counts": {"finished": 1},
            "observed_conversations": 1,
        }

    def agent_settings(self):
        return {
            "agent_kind": "Agent",
            "llm": {"model": "provider/model"},
            "tools": None,
            "mcp_config": {},
            "enable_sub_agents": False,
            "enable_switch_llm_tool": False,
            "tool_concurrency_limit": 1,
        }

    def conversation_url(self, conversation_id):
        return f"http://canvas.test/conversations/{conversation_id}"

    def run_conversation(self, conversation_id):
        self.run_calls += 1
        return None

    def wait_for_terminal(self, conversation_id, **kwargs):
        return (
            {"id": conversation_id, "execution_status": "finished"},
            [{"kind": "FinishAction"}],
        )

    def final_response(self, conversation_id):
        return (
            '{"status":"done","candidate":{"assignments":{"a":0}},'
            '"lesson":null,"summary":["done"],"next_gate":"validate"}'
        )


class CanvasWorkerTests(unittest.TestCase):
    def test_worker_allocates_distinct_attempt_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = FakeCanvasClient()
            worker = CanvasWorker(
                client,
                workspace_root=Path(temp_dir),
                poll_seconds=0,
            )
            lifecycle = []
            execution = worker.execute(
                campaign=CampaignSpec(
                    id="campaign",
                    name="Test campaign",
                    policy="managed",
                    attempt_budget=1,
                    repository=None,
                    branch=None,
                    model=None,
                    tasks=(),
                ),
                task=TaskSpec(
                    id="task",
                    family="graph-coloring",
                    description="color one node",
                    tags=(),
                    nodes=("a",),
                    edges=(),
                    target_score=1,
                ),
                run_id="run-1",
                attempt_id="attempt-1",
                lessons=[],
                on_lifecycle=lambda event, data: lifecycle.append((event, data)),
            )
            self.assertEqual(execution.worker_kind, "canvas")
            self.assertEqual(
                client.workspace,
                Path(temp_dir) / "campaign" / "run-1" / "attempt-1",
            )
            self.assertTrue(client.workspace.is_dir())
            self.assertEqual(
                client.settings["llm"]["model"],
                "provider/model",
            )
            self.assertEqual(client.run_calls, 0)
            self.assertEqual(
                execution.conversation["conversation_id"],
                "conversation-1",
            )
            self.assertIn(
                "canvas_preflight",
                [event for event, _ in lifecycle],
            )
            self.assertIn(
                "canvas_capacity_checked",
                [event for event, _ in lifecycle],
            )

    def test_worker_refuses_native_run_without_model_access(self) -> None:
        class NoModelClient(FakeCanvasClient):
            def preflight(self):
                return {
                    "health": "ok",
                    "ready": "ready",
                    "llm_api_key_is_set": False,
                    "model": "provider/model",
                    "active_profile": "test-profile",
                }

        with tempfile.TemporaryDirectory() as temp_dir:
            worker = CanvasWorker(
                NoModelClient(),
                workspace_root=Path(temp_dir),
            )
            with self.assertRaisesRegex(RuntimeError, "no configured LLM access"):
                worker.execute(
                    campaign=CampaignSpec(
                        id="campaign",
                        name="Test campaign",
                        policy="managed",
                        attempt_budget=1,
                        repository=None,
                        branch=None,
                        model=None,
                        tasks=(),
                    ),
                    task=TaskSpec(
                        id="task",
                        family="graph-coloring",
                        description="color one node",
                        tags=(),
                        nodes=("a",),
                        edges=(),
                        target_score=1,
                    ),
                    run_id="run-1",
                    attempt_id="attempt-1",
                    lessons=[],
                    on_lifecycle=lambda event, data: None,
                )

    def test_worker_uses_remote_workspace_without_local_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            remote_root = Path(temp_dir) / "remote-canvas"
            client = FakeCanvasClient()
            worker = CanvasWorker(
                client,
                workspace_root=remote_root,
                prepare_workspace_locally=False,
                poll_seconds=0,
            )
            lifecycle = []
            worker.execute(
                campaign=CampaignSpec(
                    id="campaign",
                    name="Test campaign",
                    policy="managed",
                    attempt_budget=1,
                    repository=None,
                    branch=None,
                    model=None,
                    tasks=(),
                ),
                task=TaskSpec(
                    id="task",
                    family="graph-coloring",
                    description="color one node",
                    tags=(),
                    nodes=("a",),
                    edges=(),
                    target_score=1,
                ),
                run_id="run-1",
                attempt_id="attempt-1",
                lessons=[],
                on_lifecycle=lambda event, data: lifecycle.append((event, data)),
            )
            self.assertEqual(
                client.workspace,
                remote_root / "campaign" / "run-1" / "attempt-1",
            )
            self.assertFalse(remote_root.exists())
            self.assertFalse(client.resolve_workspace_locally)
            started = next(data for event, data in lifecycle if event == "worker_started")
            self.assertEqual(started["workspace_scope"], "canvas-remote")


if __name__ == "__main__":
    unittest.main()

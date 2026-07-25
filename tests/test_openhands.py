import unittest

from research_lab.openhands import (
    OpenHandsClient,
    latest_agent_text,
    sanitize_metadata,
    terminal_status_from_events,
)


class OpenHandsHelpersTests(unittest.TestCase):
    def test_sanitizes_secrets_but_keeps_token_usage(self) -> None:
        value = {
            "session_api_key": "secret",
            "nested": {
                "password": "secret",
                "token_usage": {"prompt_tokens": 10},
                "initial_message": {"content": [{"text": "private task"}]},
            },
        }
        self.assertEqual(
            sanitize_metadata(value),
            {
                "nested": {
                    "token_usage": {"prompt_tokens": 10},
                    "initial_message": "<redacted-content>",
                }
            },
        )

    def test_recovers_terminal_status_and_final_text(self) -> None:
        events = [
            {
                "kind": "ActionEvent",
                "source": "agent",
                "action": {"kind": "FinishAction", "message": '{"status":"done"}'},
            }
        ]
        self.assertEqual(terminal_status_from_events(events), "finished")
        self.assertEqual(latest_agent_text(events), '{"status":"done"}')

    def test_ignores_streaming_delta_when_final_message_is_not_indexed(self) -> None:
        events = [
            {
                "kind": "StreamingDeltaEvent",
                "source": "agent",
                "content": [{"type": "text", "text": '{"status":"do'}],
            }
        ]
        self.assertEqual(latest_agent_text(events), "")

    def test_wait_for_terminal_uses_durable_events(self) -> None:
        def requester(method, url, headers, body=None, timeout=60):
            if "/api/v1/app-conversations?" in url:
                return [{"sandbox_status": "PAUSED", "execution_status": ""}]
            if "/events/search" in url:
                return {
                    "items": [
                        {
                            "kind": "ConversationStateUpdateEvent",
                            "source": "environment",
                            "key": "execution_status",
                            "value": "finished",
                        }
                    ],
                    "next_page_id": None,
                }
            raise AssertionError(url)

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
            sleeper=lambda _: None,
            monotonic=lambda: 0,
        )
        record, events, recovered = client.wait_for_terminal("conversation-1")
        self.assertEqual(record["execution_status"], "finished")
        self.assertTrue(recovered)
        self.assertEqual(len(events), 1)

    def test_pause_sandbox_waits_for_paused_and_sanitizes_record(self) -> None:
        calls = []

        def requester(method, url, headers, body=None, timeout=60):
            calls.append((method, url))
            if method == "POST" and url.endswith("/sandboxes/sandbox-1/pause"):
                return {"success": True}
            if method == "GET" and "/api/v1/sandboxes?" in url:
                return [
                    {
                        "id": "sandbox-1",
                        "status": "PAUSED",
                        "session_api_key": "do-not-persist",
                    }
                ]
            raise AssertionError((method, url))

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
            sleeper=lambda _: None,
            monotonic=lambda: 0,
        )
        record = client.pause_sandbox("sandbox-1")
        self.assertEqual(record, {"id": "sandbox-1", "status": "PAUSED"})
        self.assertEqual([method for method, _ in calls], ["POST", "GET"])

    def test_capacity_snapshot_paginates_and_counts_only_active_states(self) -> None:
        def requester(method, url, headers, body=None, timeout=60):
            self.assertEqual(method, "GET")
            if "page_id=page-2" in url:
                return {
                    "items": [
                        {"id": "sandbox-3", "status": "STARTING"},
                        {"id": "sandbox-4", "status": "ERROR"},
                    ],
                    "next_page_id": None,
                }
            return {
                "items": [
                    {"id": "sandbox-1", "status": "RUNNING"},
                    {"id": "sandbox-2", "status": "PAUSED"},
                ],
                "next_page_id": "page-2",
            }

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
        )
        snapshot = client.capacity_snapshot(runtime_limit=10, launch_lock_at=3)
        self.assertEqual(snapshot["active"], 2)
        self.assertEqual(snapshot["observed_sandboxes"], 4)
        self.assertTrue(snapshot["launch_allowed"])
        self.assertEqual(
            snapshot["status_counts"],
            {"ERROR": 1, "PAUSED": 1, "RUNNING": 1, "STARTING": 1},
        )

    def test_capacity_snapshot_closes_gate_at_threshold(self) -> None:
        def requester(method, url, headers, body=None, timeout=60):
            return {
                "items": [
                    {"id": f"sandbox-{index}", "status": "RUNNING"}
                    for index in range(7)
                ]
            }

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
        )
        snapshot = client.capacity_snapshot(runtime_limit=10, launch_lock_at=7)
        self.assertEqual(snapshot["active"], 7)
        self.assertFalse(snapshot["launch_allowed"])


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

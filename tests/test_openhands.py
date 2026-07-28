import unittest

from research_lab.enterprise_events import terminal_signal, websocket_url
from research_lab.openhands import (
    OpenHandsAPIError,
    OpenHandsClient,
    ResilientRequester,
    latest_agent_text,
    sanitize_metadata,
    streaming_agent_text,
    terminal_status_from_events,
)


class OpenHandsHelpersTests(unittest.TestCase):
    def test_retries_transient_get_failures_and_records_metrics(self) -> None:
        calls = 0

        def requester(method, url, headers, body=None, timeout=60):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OpenHandsAPIError(
                    "GET /api/v1/users/me -> HTTP 401: BearerTokenError"
                )
            if calls == 2:
                raise OpenHandsAPIError(
                    "GET /api/v1/users/me -> HTTP 503: unavailable"
                )
            return {"id": "user-1"}

        delays = []
        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
            sleeper=delays.append,
        )
        self.assertEqual(client.preflight(), {"id": "user-1"})
        self.assertEqual(calls, 3)
        self.assertEqual(delays, [1.0, 2.0])
        self.assertEqual(
            client.retry_metrics(),
            {
                "rate_limit": 0,
                "transient_auth": 1,
                "server": 1,
                "transport": 0,
            },
        )

    def test_does_not_retry_ambiguous_conversation_create_failure(self) -> None:
        calls = 0

        def requester(method, url, headers, body=None, timeout=60):
            nonlocal calls
            calls += 1
            raise OpenHandsAPIError(
                "POST /api/v1/app-conversations -> HTTP 503: unavailable"
            )

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
            sleeper=lambda _: None,
        )
        with self.assertRaises(OpenHandsAPIError):
            client.start_conversation(
                prompt="test",
                title="test",
                repository=None,
                branch=None,
                model=None,
            )
        self.assertEqual(calls, 1)

    def test_retries_rejected_rate_limited_post(self) -> None:
        calls = 0

        def requester(method, url, headers, body=None, timeout=60):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OpenHandsAPIError(
                    "POST /api/v1/app-conversations -> HTTP 429: busy"
                )
            return {"id": "start-1"}

        requester_with_retries = ResilientRequester(
            requester,
            sleeper=lambda _: None,
        )
        result = requester_with_retries(
            "POST",
            "https://example.test/api/v1/app-conversations",
            {},
            body={},
        )
        self.assertEqual(result, {"id": "start-1"})
        self.assertEqual(calls, 2)

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
        self.assertEqual(streaming_agent_text(events), '{"status":"do')

    def test_streaming_recovery_uses_only_latest_contiguous_agent_block(self) -> None:
        events = [
            {
                "kind": "StreamingDeltaEvent",
                "source": "agent",
                "content": "old reasoning",
            },
            {
                "kind": "ObservationEvent",
                "source": "environment",
                "content": "tool result",
            },
            {
                "kind": "StreamingDeltaEvent",
                "source": "agent",
                "content": '{"status":"done"',
            },
            {
                "kind": "StreamingDeltaEvent",
                "source": "agent",
                "content": "}",
            },
        ]
        self.assertEqual(streaming_agent_text(events), '{"status":"done"}')

    def test_final_response_recovers_terminal_streaming_text(self) -> None:
        def requester(method, url, headers, body=None, timeout=60):
            if "sort_order=TIMESTAMP_DESC" in url:
                return {
                    "items": [
                        {
                            "kind": "StreamingDeltaEvent",
                            "source": "agent",
                            "content": "}",
                        },
                        {
                            "kind": "StreamingDeltaEvent",
                            "source": "agent",
                            "content": '{"status":"done"',
                        },
                    ]
                }
            return {"items": []}

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
            sleeper=lambda _: None,
        )
        text, events = client.final_response("conversation-1")
        self.assertEqual(text, '{"status":"done"}')
        self.assertEqual(
            events[-1]["kind"],
            "ControllerRecoveredStreamingText",
        )

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

    def test_wait_for_terminal_does_not_scan_events_while_runtime_is_active(
        self,
    ) -> None:
        conversation_reads = 0
        event_reads = 0

        def requester(method, url, headers, body=None, timeout=60):
            nonlocal conversation_reads, event_reads
            if "/api/v1/app-conversations?" in url:
                conversation_reads += 1
                if conversation_reads == 1:
                    return [{"sandbox_status": "RUNNING", "execution_status": ""}]
                return [
                    {
                        "sandbox_status": "RUNNING",
                        "execution_status": "finished",
                    }
                ]
            if "/events/search" in url:
                event_reads += 1
                return {"items": [], "next_page_id": None}
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
        self.assertFalse(recovered)
        self.assertEqual(events, [])
        self.assertEqual(event_reads, 1)

    def test_wait_for_terminal_continues_after_exhausted_transient_read(
        self,
    ) -> None:
        conversation_reads = 0

        def requester(method, url, headers, body=None, timeout=60):
            nonlocal conversation_reads
            if "/api/v1/app-conversations?" in url:
                conversation_reads += 1
                if conversation_reads == 1:
                    raise OpenHandsAPIError(
                        "GET /api/v1/app-conversations -> HTTP 401: "
                        "BearerTokenError"
                    )
                return [
                    {
                        "sandbox_status": "RUNNING",
                        "execution_status": "finished",
                    }
                ]
            if "/events/search" in url:
                return {"items": [], "next_page_id": None}
            raise AssertionError(url)

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
            sleeper=lambda _: None,
            monotonic=lambda: 0,
            transient_retries=0,
        )
        record, _, _ = client.wait_for_terminal("conversation-1")
        self.assertEqual(record["execution_status"], "finished")
        self.assertEqual(conversation_reads, 2)

    def test_fetch_events_can_bound_page_scans(self) -> None:
        calls = 0

        def requester(method, url, headers, body=None, timeout=60):
            nonlocal calls
            calls += 1
            return {
                "items": [{"kind": "MessageEvent", "source": "agent"}],
                "next_page_id": f"page-{calls + 1}",
            }

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
        )
        events = client.fetch_events(
            "conversation-1",
            sort_order="TIMESTAMP_DESC",
            max_pages=2,
        )
        self.assertEqual(calls, 2)
        self.assertEqual(len(events), 2)

    def test_final_response_reads_descending_tail_when_head_is_truncated(self) -> None:
        calls = []

        def requester(method, url, headers, body=None, timeout=60):
            calls.append(url)
            if "sort_order=TIMESTAMP_DESC" in url:
                return {
                    "items": [
                        {
                            "kind": "MessageEvent",
                            "source": "agent",
                            "llm_message": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": '{"status":"done"}',
                                    }
                                ]
                            },
                        }
                    ]
                }
            return {
                "items": [
                    {
                        "kind": "StreamingDeltaEvent",
                        "source": "agent",
                    }
                ]
            }

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
            sleeper=lambda _: None,
        )
        text, events = client.final_response(
            "conversation-1",
            retries=1,
        )
        self.assertEqual(text, '{"status":"done"}')
        self.assertEqual(len(events), 1)
        self.assertTrue(
            any("sort_order=TIMESTAMP_DESC" in url for url in calls)
        )

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

    def test_sets_and_verifies_sandbox_grouping_strategy(self) -> None:
        calls = []

        def requester(method, url, headers, body=None, timeout=60):
            calls.append((method, url, body))
            if method == "POST" and url.endswith("/api/v1/settings"):
                return True
            if method == "GET" and url.endswith("/api/v1/users/me"):
                return {"sandbox_grouping_strategy": "NO_GROUPING"}
            raise AssertionError((method, url))

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
        )
        self.assertEqual(
            client.set_sandbox_grouping_strategy("NO_GROUPING"),
            "NO_GROUPING",
        )
        self.assertEqual(
            calls[0],
            (
                "POST",
                "https://example.test/api/v1/settings",
                {"sandbox_grouping_strategy": "NO_GROUPING"},
            ),
        )

    def test_rejects_unknown_sandbox_grouping_strategy(self) -> None:
        client = OpenHandsClient("https://example.test", "not-logged")
        with self.assertRaisesRegex(ValueError, "unknown sandbox grouping"):
            client.set_sandbox_grouping_strategy("RANDOM")

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

    def test_explicit_sandbox_attach_and_cleanup_endpoints(self) -> None:
        calls = []

        def requester(method, url, headers, body=None, timeout=60):
            calls.append((method, url, body))
            if method == "POST" and url.endswith("/api/v1/sandboxes"):
                return {"id": "sandbox-1", "status": "STARTING"}
            if method == "POST" and url.endswith("/api/v1/app-conversations"):
                return {"id": "start-1"}
            if method == "DELETE":
                return {"success": True}
            raise AssertionError((method, url))

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
        )
        self.assertEqual(client.start_sandbox()["id"], "sandbox-1")
        client.start_conversation(
            prompt="test",
            title="test",
            repository=None,
            branch=None,
            model=None,
            sandbox_id="sandbox-1",
            secrets={"SCOPED_TOKEN": "not-logged"},
        )
        client.delete_conversation("conversation-1")
        client.delete_sandbox("sandbox-1")
        self.assertEqual(
            calls[1][2]["sandbox_id"],
            "sandbox-1",
        )
        self.assertEqual(
            calls[1][2]["secrets"],
            {"SCOPED_TOKEN": "not-logged"},
        )
        self.assertIn(
            "sandbox_id=sandbox-1",
            calls[3][1],
        )

    def test_agent_tags_merge_and_server_info(self) -> None:
        agent_url = (
            "https://runtime.example.test/api/conversations/conversation-1"
        )
        agent_gets = 0

        def requester(method, url, headers, body=None, timeout=60):
            nonlocal agent_gets
            if url.endswith("/api/v1/app-conversations?ids=conversation-1"):
                return [
                    {
                        "id": "conversation-1",
                        "conversation_url": agent_url,
                        "session_api_key": "not-logged",
                    }
                ]
            if method == "GET" and url == agent_url:
                agent_gets += 1
                return {
                    "tags": (
                        {"existing": "yes"}
                        if agent_gets == 1
                        else {"existing": "yes", "campaignid": "campaign-1"}
                    )
                }
            if method == "PATCH" and url == agent_url:
                self.assertEqual(
                    body,
                    {"tags": {"existing": "yes", "campaignid": "campaign-1"}},
                )
                return {"success": True}
            if method == "GET" and url.endswith("/server_info"):
                return {
                    "idle_time": 12.0,
                    "runtime_idle_timeout_seconds": 1200.0,
                }
            raise AssertionError((method, url))

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
        )
        self.assertEqual(
            client.patch_agent_tags(
                "conversation-1",
                {"campaignid": "campaign-1"},
            ),
            {"existing": "yes", "campaignid": "campaign-1"},
        )
        self.assertEqual(
            client.get_agent_server_info("conversation-1")["idle_time"],
            12.0,
        )

    def test_null_tombstones_are_normalized_to_missing_records(self) -> None:
        def requester(method, url, headers, body=None, timeout=60):
            return [None]

        client = OpenHandsClient(
            "https://example.test",
            "not-logged",
            requester=requester,
        )
        self.assertEqual(client.get_conversation("conversation-1"), {})
        self.assertEqual(client.get_sandbox("sandbox-1"), {})

    def test_websocket_terminal_confirmation(self) -> None:
        self.assertEqual(
            terminal_signal(
                {
                    "kind": "ConversationStateUpdateEvent",
                    "key": "execution_status",
                    "value": "finished",
                }
            ),
            ("finished", False),
        )
        self.assertEqual(
            terminal_signal(
                {
                    "kind": "ConversationStateUpdateEvent",
                    "key": "full_state",
                    "value": {"execution_status": "finished"},
                }
            ),
            ("finished", True),
        )
        self.assertEqual(
            websocket_url(
                "https://runtime.example.test/api/conversations/conversation-1"
            ),
            (
                "wss://runtime.example.test/sockets/events/conversation-1"
                "?resend_mode=all"
            ),
        )


if __name__ == "__main__":
    unittest.main()

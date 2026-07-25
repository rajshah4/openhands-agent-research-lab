from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any


DEFAULT_BASE_URL = "https://app.all-hands.dev"
TERMINAL_STATUSES = {
    "finished",
    "error",
    "stuck",
    "stopped",
    "waiting_for_confirmation",
}
FAILED_START_STATUSES = {"ERROR", "FAILED", "STOPPED"}
SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "credential",
    "credentials",
    "password",
    "private_key",
    "secret",
    "session_api_key",
}
CONTENT_KEYS = {"initial_message", "messages", "prompt", "system_prompt"}


class OpenHandsAPIError(RuntimeError):
    """Raised when a supported OpenHands V1 operation fails."""


def configured_base_url(explicit: str | None = None) -> str:
    return (
        explicit
        or os.getenv("OPENHANDS_BASE_URL")
        or os.getenv("OPENHANDS_HOST")
        or DEFAULT_BASE_URL
    ).rstrip("/")


def configured_api_key(explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip()
    for name in ("OPENHANDS_API_KEY", "OPENHANDS_API_KEY_ORG", "OH_API_KEY"):
        value = os.getenv(name)
        if value:
            return value.strip()
    raise OpenHandsAPIError(
        "missing OpenHands API key; set OPENHANDS_API_KEY, "
        "OPENHANDS_API_KEY_ORG, or OH_API_KEY"
    )


def _endpoint(base: str, path: str, query: dict[str, Any] | None = None) -> str:
    url = base.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)
    return url


def request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
    timeout: int = 60,
) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise OpenHandsAPIError(
            f"{method} {urllib.parse.urlsplit(url).path} -> HTTP {exc.code}: {raw[:1000]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise OpenHandsAPIError(
            f"{method} {urllib.parse.urlsplit(url).path} failed: {exc.reason}"
        ) from exc


def sanitize_metadata(value: Any) -> Any:
    """Remove secret-bearing fields while retaining usage and lifecycle metadata."""
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in SENSITIVE_KEYS or normalized.endswith("_password"):
                continue
            if normalized.endswith("_api_key") or normalized.endswith("_secret"):
                continue
            if normalized in CONTENT_KEYS:
                sanitized[str(key)] = "<redacted-content>"
                continue
            sanitized[str(key)] = sanitize_metadata(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_metadata(item) for item in value]
    return value


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type", "text") == "text":
            text = item.get("text")
            if text:
                chunks.append(str(text))
    return "\n".join(chunks)


def latest_agent_text(events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        action = event.get("action") if isinstance(event.get("action"), dict) else {}
        action_kind = str(action.get("kind", event.get("kind", "")))
        if action_kind == "FinishAction" and action.get("message"):
            return str(action["message"]).strip()
    for event in reversed(events):
        if str(event.get("source", "")).lower() not in {"agent", "assistant"}:
            continue
        if str(event.get("kind", "")) != "MessageEvent":
            continue
        for key in ("llm_message", "message"):
            message = event.get(key)
            if isinstance(message, dict):
                text = _content_text(message.get("content"))
                if text:
                    return text.strip()
        if isinstance(event.get("content"), (str, list)):
            text = _content_text(event["content"])
            if text:
                return text.strip()
    return ""


def terminal_status_from_events(events: list[dict[str, Any]]) -> str | None:
    for event in reversed(events):
        event_kind = str(event.get("kind", ""))
        action = event.get("action") if isinstance(event.get("action"), dict) else {}
        if event_kind == "FinishAction" or action.get("kind") == "FinishAction":
            return "finished"
        if event_kind in {"ConversationErrorEvent", "AgentErrorEvent", "ErrorEvent"}:
            return "error"
        if event_kind != "ConversationStateUpdateEvent":
            continue
        key = str(event.get("key", "")).lower()
        value = event.get("value")
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                value = parsed
            except json.JSONDecodeError:
                pass
        if key == "execution_status":
            status = str(value).lower()
            if status in TERMINAL_STATUSES:
                return status
        if key == "full_state" and isinstance(value, dict):
            status = str(value.get("execution_status", "")).lower()
            if status in TERMINAL_STATUSES:
                return status
    return None


class OpenHandsClient:
    """Dependency-free client for supported V1 app-conversation endpoints.

    The API flow is adapted from rajshah4/openhands-multi-agent-demo and the
    tested Rajistics Enterprise orchestration guidance.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        requester: Callable[..., Any] = request_json,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._request = requester
        self._sleep = sleeper
        self._monotonic = monotonic

    def preflight(self) -> dict[str, Any]:
        record = self._request(
            "GET",
            _endpoint(self.base_url, "/api/v1/users/me"),
            self.headers,
            timeout=30,
        )
        return sanitize_metadata(record or {})

    def start_conversation(
        self,
        *,
        prompt: str,
        title: str,
        repository: str | None,
        branch: str | None,
        model: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": title,
            "trigger": "openhands_api",
            "initial_message": {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
                "run": True,
            },
        }
        if repository:
            payload["selected_repository"] = repository
        if branch:
            payload["selected_branch"] = branch
        if model:
            payload["llm_model"] = model
        response = self._request(
            "POST",
            _endpoint(self.base_url, "/api/v1/app-conversations"),
            self.headers,
            body=payload,
            timeout=120,
        )
        if not isinstance(response, dict) or not response.get("id"):
            raise OpenHandsAPIError("conversation create returned no start-task id")
        return response

    def poll_start_task(
        self,
        task_id: str,
        *,
        timeout_seconds: int = 600,
        poll_seconds: int = 10,
    ) -> dict[str, Any]:
        deadline = self._monotonic() + timeout_seconds
        while self._monotonic() < deadline:
            tasks = self._request(
                "GET",
                _endpoint(
                    self.base_url,
                    "/api/v1/app-conversations/start-tasks",
                    {"ids": task_id},
                ),
                self.headers,
                timeout=60,
            )
            task = tasks[0] if isinstance(tasks, list) and tasks else {}
            status = str(task.get("status", "")).upper()
            if task.get("app_conversation_id"):
                return task
            if status in FAILED_START_STATUSES:
                raise OpenHandsAPIError(f"start task {task_id} ended with {status}")
            self._sleep(poll_seconds)
        raise TimeoutError(f"timed out waiting for OpenHands start task {task_id}")

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        records = self._request(
            "GET",
            _endpoint(
                self.base_url,
                "/api/v1/app-conversations",
                {"ids": conversation_id},
            ),
            self.headers,
            timeout=60,
        )
        return records[0] if isinstance(records, list) and records else {}

    def get_sandbox(self, sandbox_id: str) -> dict[str, Any]:
        records = self._request(
            "GET",
            _endpoint(
                self.base_url,
                "/api/v1/sandboxes",
                {"id": sandbox_id},
            ),
            self.headers,
            timeout=60,
        )
        return records[0] if isinstance(records, list) and records else {}

    def pause_sandbox(
        self,
        sandbox_id: str,
        *,
        timeout_seconds: int = 120,
        poll_seconds: int = 2,
    ) -> dict[str, Any]:
        response = self._request(
            "POST",
            _endpoint(
                self.base_url,
                f"/api/v1/sandboxes/{urllib.parse.quote(sandbox_id, safe='')}/pause",
            ),
            self.headers,
            timeout=60,
        )
        if isinstance(response, dict) and response.get("success") is False:
            raise OpenHandsAPIError(f"sandbox {sandbox_id} rejected pause request")

        deadline = self._monotonic() + timeout_seconds
        while self._monotonic() < deadline:
            record = self.get_sandbox(sandbox_id)
            status = str(record.get("status", "")).upper()
            if status == "PAUSED":
                return sanitize_metadata(record)
            if status in {"ERROR", "MISSING"}:
                raise OpenHandsAPIError(
                    f"sandbox {sandbox_id} reached {status} while pausing"
                )
            self._sleep(poll_seconds)
        raise TimeoutError(f"timed out pausing OpenHands sandbox {sandbox_id}")

    def fetch_events(self, conversation_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        page_id: str | None = None
        while True:
            query: dict[str, Any] = {"sort_order": "TIMESTAMP", "limit": limit}
            if page_id:
                query["page_id"] = page_id
            page = self._request(
                "GET",
                _endpoint(
                    self.base_url,
                    f"/api/v1/conversation/{conversation_id}/events/search",
                    query,
                ),
                self.headers,
                timeout=60,
            )
            if not isinstance(page, dict):
                return events
            events.extend(item for item in page.get("items", []) if isinstance(item, dict))
            page_id = page.get("next_page_id")
            if not page_id:
                return events

    def wait_for_terminal(
        self,
        conversation_id: str,
        *,
        timeout_seconds: int = 1800,
        poll_seconds: int = 20,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
        deadline = self._monotonic() + timeout_seconds
        last_record: dict[str, Any] = {}
        last_events: list[dict[str, Any]] = []
        while self._monotonic() < deadline:
            last_record = self.get_conversation(conversation_id)
            status = str(last_record.get("execution_status", "")).lower()
            if status in TERMINAL_STATUSES:
                return last_record, self.fetch_events(conversation_id), False

            sandbox_status = str(last_record.get("sandbox_status", "")).upper()
            if not status or sandbox_status in {"PAUSED", "ERROR", "MISSING"}:
                last_events = self.fetch_events(conversation_id)
                recovered = terminal_status_from_events(last_events)
                if recovered:
                    recovered_record = dict(last_record)
                    recovered_record["execution_status"] = recovered
                    recovered_record["terminal_status_source"] = "events"
                    return recovered_record, last_events, True
                if sandbox_status in {"ERROR", "MISSING"}:
                    raise OpenHandsAPIError(
                        f"conversation {conversation_id} sandbox is {sandbox_status}"
                    )
            self._sleep(poll_seconds)
        raise TimeoutError(f"timed out waiting for OpenHands conversation {conversation_id}")

    def final_response(
        self,
        conversation_id: str,
        *,
        initial_events: list[dict[str, Any]] | None = None,
        retries: int = 4,
        retry_seconds: int = 5,
    ) -> tuple[str, list[dict[str, Any]]]:
        events = initial_events or []
        for attempt in range(retries + 1):
            if not events or attempt:
                events = self.fetch_events(conversation_id)
            text = latest_agent_text(events)
            if text:
                return text, events
            if attempt < retries:
                self._sleep(retry_seconds)
        return "", events

    def conversation_url(self, conversation_id: str) -> str:
        return f"{self.base_url}/conversations/{conversation_id}"

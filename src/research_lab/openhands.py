from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from threading import Lock
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
ACTIVE_SANDBOX_STATUSES = {"RUNNING", "STARTING", "PENDING", "CREATING"}
SANDBOX_GROUPING_STRATEGIES = {
    "NO_GROUPING",
    "GROUP_BY_NEWEST",
    "LEAST_RECENTLY_USED",
    "FEWEST_CONVERSATIONS",
    "ADD_TO_ANY",
}
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


class OpenHandsCapacityError(OpenHandsAPIError):
    """Raised before launch when the configured runtime safety gate is closed."""


def is_transient_api_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    if not isinstance(exc, OpenHandsAPIError):
        return False
    message = str(exc)
    return (
        ("HTTP 401" in message and "BearerTokenError" in message)
        or "HTTP 429" in message
        or any(f"HTTP {status}" in message for status in range(500, 600))
        or " failed:" in message
    )


class ResilientRequester:
    """Bounded retries for transient API failures, with duplicate-safe writes.

    GET requests may retry rate limits, transient authentication failures,
    server errors, and transport failures. Mutating requests retry only 429 and
    the observed transient BearerTokenError 401 because those responses confirm
    that the server rejected the request before doing work.
    """

    def __init__(
        self,
        requester: Callable[..., Any],
        *,
        sleeper: Callable[[float], None] = time.sleep,
        max_retries: int = 4,
        base_delay_seconds: float = 1.0,
    ):
        if max_retries < 0:
            raise ValueError("max_retries must be at least 0")
        if base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be non-negative")
        self.requester = requester
        self.sleeper = sleeper
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self._lock = Lock()
        self._counts = {
            "rate_limit": 0,
            "transient_auth": 0,
            "server": 0,
            "transport": 0,
        }

    def __call__(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
        timeout: int = 60,
    ) -> Any:
        normalized_method = method.upper()
        for retry in range(self.max_retries + 1):
            try:
                return self.requester(
                    method,
                    url,
                    headers,
                    body=body,
                    timeout=timeout,
                )
            except (TimeoutError, ConnectionError) as exc:
                category = "transport"
                retryable = normalized_method == "GET"
                error = exc
            except OpenHandsAPIError as exc:
                message = str(exc)
                if "HTTP 429" in message:
                    category = "rate_limit"
                    retryable = True
                elif "HTTP 401" in message and "BearerTokenError" in message:
                    category = "transient_auth"
                    retryable = True
                elif any(f"HTTP {status}" in message for status in range(500, 600)):
                    category = "server"
                    retryable = normalized_method == "GET"
                elif " failed:" in message:
                    category = "transport"
                    retryable = normalized_method == "GET"
                else:
                    raise
                error = exc
            if not retryable or retry >= self.max_retries:
                raise error
            with self._lock:
                self._counts[category] += 1
            self.sleeper(
                min(self.base_delay_seconds * (2**retry), 8.0)
            )
        raise AssertionError("unreachable")

    def metrics(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)


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
        safe_detail = raw
        try:
            safe_detail = json.dumps(
                sanitize_metadata(json.loads(raw)),
                sort_keys=True,
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            safe_detail = "<non-json response omitted>"
        raise OpenHandsAPIError(
            f"{method} {urllib.parse.urlsplit(url).path} -> "
            f"HTTP {exc.code}: {safe_detail[:1000]}"
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


def streaming_agent_text(events: list[dict[str, Any]]) -> str:
    """Reconstruct the latest terminal streaming block.

    Long conversations may contain streaming deltas from many separate model
    turns. Only the newest contiguous block can represent the final response;
    concatenating the entire conversation produces an invalid contract.
    """
    chunks: list[str] = []
    latest_chunks: list[str] = []
    for event in events:
        if str(event.get("source", "")).lower() not in {"agent", "assistant"}:
            if chunks:
                latest_chunks = chunks
                chunks = []
            continue
        if str(event.get("kind", "")) != "StreamingDeltaEvent":
            if chunks:
                latest_chunks = chunks
                chunks = []
            continue
        content = event.get("content")
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            chunks.append(_content_text(content))
    if chunks:
        latest_chunks = chunks
    return "".join(latest_chunks).strip()


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
        transient_retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._resilient_requester = ResilientRequester(
            requester,
            sleeper=sleeper,
            max_retries=transient_retries,
        )
        self._request = self._resilient_requester
        self._sleep = sleeper
        self._monotonic = monotonic

    def retry_metrics(self) -> dict[str, int]:
        return self._resilient_requester.metrics()

    def preflight(self) -> dict[str, Any]:
        record = self._request(
            "GET",
            _endpoint(self.base_url, "/api/v1/users/me"),
            self.headers,
            timeout=30,
        )
        return sanitize_metadata(record or {})

    def set_sandbox_grouping_strategy(self, strategy: str) -> str:
        if strategy not in SANDBOX_GROUPING_STRATEGIES:
            raise ValueError(f"unknown sandbox grouping strategy: {strategy}")
        self._request(
            "POST",
            _endpoint(self.base_url, "/api/v1/settings"),
            self.headers,
            body={"sandbox_grouping_strategy": strategy},
            timeout=30,
        )
        observed = str(
            self.preflight().get("sandbox_grouping_strategy") or ""
        )
        if observed != strategy:
            raise OpenHandsAPIError(
                f"sandbox grouping strategy is {observed!r}, "
                f"expected {strategy!r}"
            )
        return observed

    def search_sandboxes(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return all sandboxes visible to the authenticated OpenHands user."""
        sandboxes: list[dict[str, Any]] = []
        page_id: str | None = None
        while True:
            query: dict[str, Any] = {"limit": limit}
            if page_id:
                query["page_id"] = page_id
            page = self._request(
                "GET",
                _endpoint(self.base_url, "/api/v1/sandboxes/search", query),
                self.headers,
                timeout=60,
            )
            if isinstance(page, list):
                sandboxes.extend(item for item in page if isinstance(item, dict))
                break
            if not isinstance(page, dict):
                break
            sandboxes.extend(
                item for item in page.get("items", []) if isinstance(item, dict)
            )
            page_id = page.get("next_page_id")
            if not page_id:
                break
        return [sanitize_metadata(record) for record in sandboxes]

    def capacity_snapshot(
        self,
        *,
        runtime_limit: int = 10,
        launch_lock_at: int = 7,
    ) -> dict[str, Any]:
        if runtime_limit < 1:
            raise ValueError("runtime_limit must be at least 1")
        if not 1 <= launch_lock_at <= runtime_limit:
            raise ValueError("launch_lock_at must be between 1 and runtime_limit")
        sandboxes = self.search_sandboxes()
        status_counts: dict[str, int] = {}
        for sandbox in sandboxes:
            status = str(sandbox.get("status", "UNKNOWN")).upper()
            status_counts[status] = status_counts.get(status, 0) + 1
        active = sum(
            count
            for status, count in status_counts.items()
            if status in ACTIVE_SANDBOX_STATUSES
        )
        return {
            "scope": "authenticated-user-visible-sandboxes",
            "active": active,
            "runtime_limit": runtime_limit,
            "launch_lock_at": launch_lock_at,
            "launch_allowed": active < launch_lock_at,
            "available_before_limit": max(runtime_limit - active, 0),
            "status_counts": dict(sorted(status_counts.items())),
            "observed_sandboxes": len(sandboxes),
        }

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
            task = self.get_start_task(task_id)
            status = str(task.get("status", "")).upper()
            if task.get("app_conversation_id"):
                return task
            if status in FAILED_START_STATUSES:
                raise OpenHandsAPIError(f"start task {task_id} ended with {status}")
            self._sleep(poll_seconds)
        raise TimeoutError(f"timed out waiting for OpenHands start task {task_id}")

    def get_start_task(self, task_id: str) -> dict[str, Any]:
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
        return sanitize_metadata(task)

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

    def fetch_events(
        self,
        conversation_id: str,
        *,
        limit: int = 100,
        sort_order: str = "TIMESTAMP",
        max_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        if sort_order not in {"TIMESTAMP", "TIMESTAMP_DESC"}:
            raise ValueError(f"unknown event sort order: {sort_order}")
        if max_pages is not None and max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        events: list[dict[str, Any]] = []
        page_id: str | None = None
        pages = 0
        while True:
            query: dict[str, Any] = {
                "sort_order": sort_order,
                "limit": limit,
            }
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
            pages += 1
            page_id = page.get("next_page_id")
            if not page_id or (max_pages is not None and pages >= max_pages):
                return (
                    list(reversed(events))
                    if sort_order == "TIMESTAMP_DESC"
                    else events
                )

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
            try:
                last_record = self.get_conversation(conversation_id)
                status = str(last_record.get("execution_status", "")).lower()
                if status in TERMINAL_STATUSES:
                    return (
                        last_record,
                        self.fetch_events(
                            conversation_id,
                            sort_order="TIMESTAMP_DESC",
                            max_pages=2,
                        ),
                        False,
                    )

                sandbox_status = str(last_record.get("sandbox_status", "")).upper()
                if sandbox_status in {"PAUSED", "ERROR", "MISSING"}:
                    last_events = self.fetch_events(
                        conversation_id,
                        sort_order="TIMESTAMP_DESC",
                        max_pages=2,
                    )
                    recovered = terminal_status_from_events(last_events)
                    if recovered:
                        recovered_record = dict(last_record)
                        recovered_record["execution_status"] = recovered
                        recovered_record["terminal_status_source"] = "events"
                        return recovered_record, last_events, True
                    if sandbox_status in {"ERROR", "MISSING"}:
                        raise OpenHandsAPIError(
                            f"conversation {conversation_id} sandbox is "
                            f"{sandbox_status}"
                        )
            except (OpenHandsAPIError, TimeoutError, ConnectionError) as exc:
                if not is_transient_api_error(exc):
                    raise
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
            try:
                if not events or attempt:
                    events = self.fetch_events(
                        conversation_id,
                        sort_order="TIMESTAMP_DESC",
                        max_pages=2,
                    )
            except (OpenHandsAPIError, TimeoutError, ConnectionError) as exc:
                if not is_transient_api_error(exc) or attempt >= retries:
                    raise
                self._sleep(retry_seconds)
                continue
            text = latest_agent_text(events)
            if text:
                return text, events
            # A tested Enterprise edge case marked the conversation finished
            # but indexed only StreamingDeltaEvents. At this point the caller
            # has already observed terminal state, so reconstruct the bounded
            # response rather than treating an absent MessageEvent as no work.
            streamed_text = streaming_agent_text(events)
            if streamed_text:
                return streamed_text, [
                    *events,
                    {
                        "kind": "ControllerRecoveredStreamingText",
                        "source": "controller",
                    },
                ]
            if attempt < retries:
                self._sleep(retry_seconds)
        return "", events

    def conversation_url(self, conversation_id: str) -> str:
        return f"{self.base_url}/conversations/{conversation_id}"

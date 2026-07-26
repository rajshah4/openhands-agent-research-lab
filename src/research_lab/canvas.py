from __future__ import annotations

import copy
import time
import urllib.parse
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .domain import CampaignSpec, Lesson, TaskSpec, WorkerExecution
from .openhands import OpenHandsAPIError, request_json, sanitize_metadata
from .workers import render_worker_prompt


CANVAS_TERMINAL_STATUSES = {
    "finished",
    "error",
    "stuck",
    "paused",
    "waiting_for_confirmation",
}
CANVAS_ACTIVE_STATUSES = {"running"}


def _endpoint(base: str, path: str, query: dict[str, Any] | None = None) -> str:
    url = base.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)
    return url


def _safe_segment(value: str) -> str:
    segment = "".join(
        character if character.isalnum() or character in {"-", "_"} else "-"
        for character in value
    ).strip("-")
    if not segment:
        raise ValueError("workspace identifier produced an empty path segment")
    return segment[:128]


class CanvasClient:
    """Dependency-free client for the Agent Canvas agent-server protocol."""

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
            "X-Session-API-Key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._request = requester
        self._sleep = sleeper
        self._monotonic = monotonic

    def preflight(self) -> dict[str, Any]:
        health = self._request(
            "GET",
            _endpoint(self.base_url, "/health"),
            self.headers,
            timeout=30,
        )
        ready = self._request(
            "GET",
            _endpoint(self.base_url, "/ready"),
            self.headers,
            timeout=30,
        )
        settings = self._request(
            "GET",
            _endpoint(self.base_url, "/api/settings"),
            self.headers,
            timeout=30,
        )
        profiles = self._request(
            "GET",
            _endpoint(self.base_url, "/api/profiles"),
            self.headers,
            timeout=30,
        )
        settings = settings if isinstance(settings, dict) else {}
        profiles = profiles if isinstance(profiles, dict) else {}
        agent_settings = settings.get("agent_settings")
        model = None
        if isinstance(agent_settings, dict):
            llm = agent_settings.get("llm")
            if isinstance(llm, dict):
                model = llm.get("model")
            model = model or agent_settings.get("llm_model")
        return {
            "health": str((health or {}).get("status", "")).lower()
            if isinstance(health, dict)
            else str(health).lower(),
            "ready": str((ready or {}).get("status", "")).lower()
            if isinstance(ready, dict)
            else str(ready).lower(),
            "llm_api_key_is_set": bool(settings.get("llm_api_key_is_set")),
            "model": model,
            "active_profile": profiles.get("active_profile"),
        }

    def start_conversation(
        self,
        *,
        prompt: str,
        workspace: Path,
        max_iterations: int,
        tags: dict[str, str],
        worktree: bool = False,
        agent_settings: dict[str, Any] | None = None,
        agent_profile_id: str | None = None,
        resolve_workspace_locally: bool = True,
    ) -> dict[str, Any]:
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        workspace_path = (
            workspace.resolve() if resolve_workspace_locally else workspace
        )
        payload: dict[str, Any] = {
            "workspace": {
                "working_dir": str(workspace_path),
                "kind": "LocalWorkspace",
            },
            "worktree": worktree,
            "confirmation_policy": {"kind": "NeverConfirm"},
            "initial_message": {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
                "run": False,
            },
            "max_iterations": max_iterations,
            "stuck_detection": True,
            "tags": tags,
            "autotitle": False,
        }
        if agent_settings is not None:
            payload["agent_settings"] = agent_settings
            payload["secrets_encrypted"] = True
        elif agent_profile_id:
            payload["agent_profile_id"] = agent_profile_id
        response = self._request(
            "POST",
            _endpoint(self.base_url, "/api/conversations"),
            self.headers,
            body=payload,
            timeout=120,
        )
        if not isinstance(response, dict) or not response.get("id"):
            raise OpenHandsAPIError("Canvas conversation create returned no id")
        return sanitize_metadata(response)

    def agent_settings(self) -> dict[str, Any]:
        encrypted_headers = {
            **self.headers,
            "X-Expose-Secrets": "encrypted",
        }
        settings = self._request(
            "GET",
            _endpoint(self.base_url, "/api/settings"),
            encrypted_headers,
            timeout=30,
        )
        agent_settings = (
            settings.get("agent_settings") if isinstance(settings, dict) else None
        )
        if not isinstance(agent_settings, dict) or not agent_settings:
            raise OpenHandsAPIError(
                "Canvas backend returned no usable agent settings"
            )
        bounded_settings = copy.deepcopy(agent_settings)
        bounded_settings["tools"] = None
        bounded_settings["mcp_config"] = {}
        bounded_settings["enable_sub_agents"] = False
        bounded_settings["enable_switch_llm_tool"] = False
        bounded_settings["tool_concurrency_limit"] = 1
        return bounded_settings

    def search_conversations(self, *, limit: int = 100) -> list[dict[str, Any]]:
        conversations: list[dict[str, Any]] = []
        page_id: str | None = None
        while True:
            query: dict[str, Any] = {"limit": limit}
            if page_id:
                query["page_id"] = page_id
            page = self._request(
                "GET",
                _endpoint(
                    self.base_url,
                    "/api/conversations/search",
                    query,
                ),
                self.headers,
                timeout=60,
            )
            if not isinstance(page, dict):
                return conversations
            conversations.extend(
                sanitize_metadata(item)
                for item in page.get("items", [])
                if isinstance(item, dict)
            )
            page_id = page.get("next_page_id")
            if not page_id:
                return conversations

    def capacity_snapshot(self, *, launch_lock_at: int = 2) -> dict[str, Any]:
        if launch_lock_at < 1:
            raise ValueError("launch_lock_at must be at least 1")
        conversations = self.search_conversations()
        status_counts: dict[str, int] = {}
        for conversation in conversations:
            status = str(conversation.get("execution_status", "unknown")).lower()
            status_counts[status] = status_counts.get(status, 0) + 1
        active = sum(
            count
            for status, count in status_counts.items()
            if status in CANVAS_ACTIVE_STATUSES
        )
        return {
            "scope": "shared-canvas-conversations",
            "active": active,
            "launch_lock_at": launch_lock_at,
            "launch_allowed": active < launch_lock_at,
            "status_counts": dict(sorted(status_counts.items())),
            "observed_conversations": len(conversations),
        }

    def run_conversation(self, conversation_id: str) -> None:
        try:
            response = self._request(
                "POST",
                _endpoint(
                    self.base_url,
                    (
                        f"/api/conversations/"
                        f"{urllib.parse.quote(conversation_id, safe='')}/run"
                    ),
                ),
                self.headers,
                timeout=60,
            )
        except OpenHandsAPIError as exc:
            message = str(exc).lower()
            if "http 409" in message and "already running" in message:
                return
            raise
        if isinstance(response, dict) and response.get("success") is False:
            raise OpenHandsAPIError(
                f"Canvas conversation {conversation_id} rejected run request"
            )

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        record = self._request(
            "GET",
            _endpoint(
                self.base_url,
                f"/api/conversations/{urllib.parse.quote(conversation_id, safe='')}",
            ),
            self.headers,
            timeout=60,
        )
        return sanitize_metadata(record) if isinstance(record, dict) else {}

    def fetch_events(
        self,
        conversation_id: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
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
                    (
                        f"/api/conversations/"
                        f"{urllib.parse.quote(conversation_id, safe='')}/events/search"
                    ),
                    query,
                ),
                self.headers,
                timeout=60,
            )
            if not isinstance(page, dict):
                return events
            events.extend(
                sanitize_metadata(item)
                for item in page.get("items", [])
                if isinstance(item, dict)
            )
            page_id = page.get("next_page_id")
            if not page_id:
                return events

    def wait_for_terminal(
        self,
        conversation_id: str,
        *,
        timeout_seconds: int = 1800,
        poll_seconds: int = 10,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        deadline = self._monotonic() + timeout_seconds
        while self._monotonic() < deadline:
            record = self.get_conversation(conversation_id)
            status = str(record.get("execution_status", "")).lower()
            if status in CANVAS_TERMINAL_STATUSES:
                return record, self.fetch_events(conversation_id)
            self._sleep(poll_seconds)
        raise TimeoutError(
            f"timed out waiting for Canvas conversation {conversation_id}"
        )

    def final_response(
        self,
        conversation_id: str,
        *,
        retries: int = 4,
        retry_seconds: int = 2,
    ) -> str:
        for attempt in range(retries + 1):
            result = self._request(
                "GET",
                _endpoint(
                    self.base_url,
                    (
                        f"/api/conversations/"
                        f"{urllib.parse.quote(conversation_id, safe='')}"
                        "/agent_final_response"
                    ),
                ),
                self.headers,
                timeout=60,
            )
            response = result.get("response") if isinstance(result, dict) else None
            if response:
                return str(response).strip()
            if attempt < retries:
                self._sleep(retry_seconds)
        return ""

    def conversation_url(self, conversation_id: str) -> str:
        return (
            f"{self.base_url}/conversations/"
            f"{urllib.parse.quote(conversation_id, safe='')}"
        )


class CanvasWorker:
    """Run bounded research attempts on one shared Agent Canvas backend."""

    def __init__(
        self,
        client: CanvasClient,
        *,
        workspace_root: Path,
        max_iterations: int = 50,
        execution_timeout_seconds: int = 1800,
        poll_seconds: int = 10,
        require_model_access: bool = True,
        launch_lock_at: int = 2,
        profile: str | None = None,
        prepare_workspace_locally: bool = True,
    ):
        self.client = client
        self.workspace_root = workspace_root
        self.max_iterations = max_iterations
        self.execution_timeout_seconds = execution_timeout_seconds
        self.poll_seconds = poll_seconds
        self.require_model_access = require_model_access
        self.launch_lock_at = launch_lock_at
        self.profile = profile
        self.prepare_workspace_locally = prepare_workspace_locally

    def execute(
        self,
        *,
        campaign: CampaignSpec,
        task: TaskSpec,
        run_id: str,
        attempt_id: str,
        lessons: list[Lesson],
        on_lifecycle: Callable[[str, dict[str, Any]], None],
    ) -> WorkerExecution:
        preflight = self.client.preflight()
        on_lifecycle("canvas_preflight", preflight)
        if preflight["health"] != "ok" or preflight["ready"] != "ready":
            raise OpenHandsAPIError("Canvas backend is not healthy and ready")
        if self.require_model_access and not preflight["llm_api_key_is_set"]:
            raise OpenHandsAPIError(
                "Canvas backend has no configured LLM access for native agents"
            )
        active_profile = preflight.get("active_profile")
        if not active_profile:
            raise OpenHandsAPIError(
                "Canvas backend has no active agent profile; "
                "activate one before running the experiment"
            )
        if self.profile and self.profile != active_profile:
            raise OpenHandsAPIError(
                f"Canvas active profile is {active_profile!r}, "
                f"not the requested {self.profile!r}"
            )
        agent_settings = self.client.agent_settings()
        capacity = self.client.capacity_snapshot(
            launch_lock_at=self.launch_lock_at,
        )
        on_lifecycle("canvas_capacity_checked", capacity)
        if not capacity["launch_allowed"]:
            raise OpenHandsAPIError(
                "Canvas launch blocked: "
                f"{capacity['active']} running conversations meets or exceeds "
                f"the {capacity['launch_lock_at']} launch threshold"
            )

        workspace = (
            self.workspace_root
            / _safe_segment(campaign.id)
            / _safe_segment(run_id)
            / _safe_segment(attempt_id)
        )
        if self.prepare_workspace_locally:
            workspace.mkdir(parents=True, exist_ok=False)
        elif not workspace.is_absolute():
            raise ValueError("remote Canvas workspace root must be absolute")
        on_lifecycle(
            "worker_started",
            {
                "worker_kind": "canvas",
                "workspace": str(workspace),
                "workspace_scope": (
                    "controller-local"
                    if self.prepare_workspace_locally
                    else "canvas-remote"
                ),
            },
        )
        prompt = render_worker_prompt(
            campaign=campaign,
            task=task,
            run_id=run_id,
            attempt_id=attempt_id,
            lessons=lessons,
        )
        record = self.client.start_conversation(
            prompt=prompt,
            workspace=workspace,
            max_iterations=self.max_iterations,
            tags={
                "campaign": campaign.id[:256],
                "run": run_id[:256],
                "task": task.id[:256],
                "attempt": attempt_id[:256],
            },
            agent_settings=agent_settings,
            resolve_workspace_locally=self.prepare_workspace_locally,
        )
        conversation_id = str(record["id"])
        on_lifecycle(
            "conversation_ready",
            {
                "conversation_id": conversation_id,
                "ui_url": self.client.conversation_url(conversation_id),
                "workspace": str(workspace),
            },
        )
        auto_started = (
            str(record.get("execution_status", "")).lower() == "running"
        )
        if not auto_started:
            self.client.run_conversation(conversation_id)
        on_lifecycle(
            "conversation_running",
            {
                "conversation_id": conversation_id,
                "auto_started": auto_started,
            },
        )
        terminal, events = self.client.wait_for_terminal(
            conversation_id,
            timeout_seconds=self.execution_timeout_seconds,
            poll_seconds=self.poll_seconds,
        )
        on_lifecycle(
            "conversation_terminal",
            {
                "conversation_id": conversation_id,
                "execution_status": terminal.get("execution_status"),
            },
        )
        final_text = self.client.final_response(conversation_id)
        on_lifecycle(
            "final_response_ready",
            {
                "conversation_id": conversation_id,
                "present": bool(final_text),
                "event_count": len(events),
            },
        )
        event_counts = Counter(str(event.get("kind", "unknown")) for event in events)
        return WorkerExecution(
            final_text=final_text,
            worker_kind="canvas",
            conversation={
                "conversation_id": conversation_id,
                "ui_url": self.client.conversation_url(conversation_id),
                "execution_status": terminal.get("execution_status"),
                "workspace": str(workspace),
            },
            metadata={
                "conversation_snapshot": terminal,
                "event_count": len(events),
                "event_counts": dict(sorted(event_counts.items())),
                "shared_execution_backend": True,
            },
        )

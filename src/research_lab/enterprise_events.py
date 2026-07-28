from __future__ import annotations

import asyncio
import json
import urllib.parse
from typing import Any


def terminal_signal(event: dict[str, Any]) -> tuple[str | None, bool]:
    """Return a terminal status and whether the signal is authoritative."""
    if str(event.get("kind", "")) != "ConversationStateUpdateEvent":
        return None, False
    key = str(event.get("key", "")).lower()
    value = event.get("value")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
    if key == "full_state" and isinstance(value, dict):
        status = str(value.get("execution_status", "")).lower()
        if status in {"finished", "error", "stuck"}:
            return status, True
    if key == "execution_status":
        status = str(value).lower()
        if status in {"error", "stuck"}:
            return status, True
        if status == "finished":
            return status, False
    return None, False


def websocket_url(conversation_url: str) -> str:
    parsed = urllib.parse.urlsplit(conversation_url)
    marker = "/api/conversations/"
    if marker not in parsed.path:
        raise ValueError("unrecognized agent conversation URL")
    conversation_id = parsed.path.split(marker, 1)[1].split("/", 1)[0]
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urllib.parse.urlunsplit(
        (
            scheme,
            parsed.netloc,
            f"/sockets/events/{conversation_id}",
            "resend_mode=all",
            "",
        )
    )


async def wait_for_terminal_websocket(
    conversation_url: str,
    session_api_key: str,
    *,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Wait for an authoritative terminal state from the agent-server socket.

    The optional ``websockets`` package is imported only when this function is
    used so the core research-lab package remains dependency-free.
    """
    try:
        from websockets.asyncio.client import connect
    except ImportError as exc:
        raise RuntimeError(
            "WebSocket monitoring requires the optional 'websockets' package"
        ) from exc

    async def watch() -> dict[str, Any]:
        provisional_finished = False
        event_count = 0
        async with connect(websocket_url(conversation_url)) as socket:
            await socket.send(
                json.dumps(
                    {
                        "type": "auth",
                        "session_api_key": session_api_key,
                    }
                )
            )
            async for raw in socket:
                event_count += 1
                try:
                    event = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(event, dict):
                    continue
                status, confirmed = terminal_signal(event)
                provisional_finished = provisional_finished or (
                    status == "finished" and not confirmed
                )
                if status and confirmed:
                    return {
                        "status": status,
                        "confirmed": True,
                        "provisional_finished_observed": provisional_finished,
                        "event_count": event_count,
                    }
        raise RuntimeError("WebSocket closed before a terminal state")

    return await asyncio.wait_for(watch(), timeout=timeout_seconds)

#!/usr/bin/env python3
"""Summarize native TaskToolSet evidence without printing prompts or secrets."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from research_lab.cli import _load_env_file
from research_lab.openhands import OpenHandsClient, configured_api_key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("conversation_id")
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument(
        "--base-url",
        default="https://app.replicated.rajistics.com",
    )
    parser.add_argument("--page-limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=100)
    return parser.parse_args()


def timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def action(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("action")
    return value if isinstance(value, dict) else {}


def observation(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("observation")
    return value if isinstance(value, dict) else {}


def main() -> int:
    args = parse_args()
    _load_env_file(args.env_file)
    client = OpenHandsClient(args.base_url, configured_api_key())
    record = client.get_conversation(args.conversation_id)

    semantic_events: list[dict[str, Any]] = []
    total_events = 0
    page_id: str | None = None
    seen_pages: set[str] = set()
    pages = 0

    while pages < args.max_pages:
        query = (
            f"sort_order=TIMESTAMP_DESC&limit={args.page_limit}"
            + (f"&page_id={page_id}" if page_id else "")
        )
        page = client._request(
            "GET",
            (
                f"{args.base_url.rstrip('/')}/api/v1/conversation/"
                f"{args.conversation_id}/events/search?{query}"
            ),
            client.headers,
            timeout=60,
        )
        if not isinstance(page, dict):
            break
        items = [
            item for item in page.get("items", []) if isinstance(item, dict)
        ]
        total_events += len(items)
        semantic_events.extend(
            item for item in items if item.get("kind") != "StreamingDeltaEvent"
        )
        pages += 1
        next_page_id = page.get("next_page_id")
        if not next_page_id or next_page_id in seen_pages:
            break
        seen_pages.add(str(next_page_id))
        page_id = str(next_page_id)

    task_actions = [
        event
        for event in semantic_events
        if event.get("tool_name") == "task"
        or action(event).get("kind") == "TaskAction"
    ]
    task_observations = [
        event
        for event in semantic_events
        if event.get("tool_name") == "task"
        or observation(event).get("kind") == "TaskObservation"
    ]
    task_results = [
        {
            "task_id": observation(event).get("task_id"),
            "subagent": observation(event).get("subagent"),
            "status": observation(event).get("status"),
            "is_error": bool(observation(event).get("is_error", False)),
        }
        for event in task_observations
        if event.get("kind") == "ObservationEvent"
    ]
    system_prompt_events = [
        event
        for event in semantic_events
        if event.get("kind") == "SystemPromptEvent"
    ]
    system_prompt_shape = json.dumps(system_prompt_events, sort_keys=True)

    created_at = str(record.get("created_at") or "")
    updated_at = str(record.get("updated_at") or "")
    duration_seconds = None
    if created_at and updated_at:
        duration_seconds = round(
            (timestamp(updated_at) - timestamp(created_at)).total_seconds(),
            3,
        )

    metrics = record.get("metrics") or {}
    token_usage = metrics.get("accumulated_token_usage") or {}
    result = {
        "conversation_id": args.conversation_id,
        "sandbox_id": record.get("sandbox_id"),
        "sandbox_status": record.get("sandbox_status"),
        "execution_status": record.get("execution_status"),
        "duration_seconds": duration_seconds,
        "model_cost": metrics.get("accumulated_cost"),
        "token_usage": {
            "prompt_tokens": token_usage.get("prompt_tokens"),
            "completion_tokens": token_usage.get("completion_tokens"),
            "cache_read_tokens": token_usage.get("cache_read_tokens"),
            "cache_write_tokens": token_usage.get("cache_write_tokens"),
        },
        "pages_scanned": pages,
        "events_scanned": total_events,
        "semantic_events": len(semantic_events),
        "event_kinds": dict(
            sorted(Counter(str(event.get("kind")) for event in semantic_events).items())
        ),
        "tool_names": dict(
            sorted(
                Counter(
                    str(event.get("tool_name"))
                    for event in semantic_events
                    if event.get("tool_name")
                ).items()
            )
        ),
        "task_actions": len(task_actions),
        "task_observations": len(task_observations),
        "task_results": task_results,
        "task_tool_advertised": (
            "subagent_type" in system_prompt_shape
            and "resume" in system_prompt_shape
            and (
                "TaskToolSet" in system_prompt_shape
                or '"name": "task"' in system_prompt_shape
            )
        ),
        "native_tasktoolset_pass": (
            len(task_actions) >= 2
            and len(task_results) >= 2
            and all(item.get("status") == "completed" for item in task_results)
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

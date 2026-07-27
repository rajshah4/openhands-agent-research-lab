#!/usr/bin/env python3
"""Run one bounded Enterprise TaskTool capability check.

The check intentionally stops after one parent conversation. It verifies that
the launched agent received TaskTool before any larger subagent load test is
attempted, records only sanitized lifecycle metadata, and pauses the sandbox.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from research_lab.cli import _load_env_file
from research_lab.openhands import OpenHandsClient, configured_api_key


PROMPT = """\
This is a bounded native-subagent capability test.

In your next assistant step, use the native `task` tool exactly once with
subagent_type="code-explorer". Ask the child to return these exact two lines:

nonce: ENTERPRISE-TASKTOOL-20260727
status: child-complete

Do not use the terminal, browser, HTTP APIs, or create another first-class
OpenHands conversation. If the native task tool is unavailable, finish with:

status: unsupported
delegated: no

After the child returns, finish with:

status: done
delegated: yes
child_status: <the child's status>
nonce: <the child's nonce>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument(
        "--base-url",
        default="https://app.replicated.rajistics.com",
    )
    parser.add_argument(
        "--model",
        default="litellm_proxy/us.anthropic.claude-haiku-4-5-20251001-v1:0",
    )
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def action(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("action")
    return value if isinstance(value, dict) else {}


def observation(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("observation")
    return value if isinstance(value, dict) else {}


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    task_actions = [
        event
        for event in events
        if event.get("tool_name") == "task"
        or action(event).get("kind") == "TaskAction"
    ]
    task_observations = [
        event
        for event in events
        if event.get("tool_name") == "task"
        or observation(event).get("kind") == "TaskObservation"
    ]
    prompt_shape = json.dumps(
        [event for event in events if event.get("kind") == "SystemPromptEvent"],
        sort_keys=True,
    )
    return {
        "task_tool_advertised": (
            "subagent_type" in prompt_shape
            and "resume" in prompt_shape
            and (
                "TaskToolSet" in prompt_shape
                or '"name": "task"' in prompt_shape
            )
        ),
        "task_actions": len(task_actions),
        "task_observations": len(task_observations),
        "task_results": [
            {
                "task_id": observation(event).get("task_id"),
                "subagent": observation(event).get("subagent"),
                "status": observation(event).get("status"),
                "is_error": bool(observation(event).get("is_error", False)),
            }
            for event in task_observations
            if event.get("kind") == "ObservationEvent"
        ],
    }


def write_result(result: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(f"{output.suffix}.tmp")
        temporary.write_text(f"{rendered}\n")
        temporary.replace(output)


def main() -> int:
    args = parse_args()
    if not args.live:
        raise SystemExit("Refusing model calls without --live")

    _load_env_file(args.env_file)
    client = OpenHandsClient(args.base_url, configured_api_key())
    settings = client._request(
        "GET",
        f"{args.base_url.rstrip('/')}/api/v1/settings",
        client.headers,
        timeout=60,
    )
    agent_settings = (
        settings.get("agent_settings", {}) if isinstance(settings, dict) else {}
    )
    capacity_before = client.capacity_snapshot(
        runtime_limit=10,
        launch_lock_at=7,
    )
    preflight = {
        "enable_sub_agents": agent_settings.get("enable_sub_agents"),
        "tool_concurrency_limit": agent_settings.get("tool_concurrency_limit"),
        "capacity_before": capacity_before,
    }
    if not preflight["enable_sub_agents"]:
        write_result({"status": "preflight-failed", **preflight}, args.output)
        return 2
    if not capacity_before.get("launch_allowed"):
        write_result({"status": "capacity-blocked", **preflight}, args.output)
        return 2

    started = time.monotonic()
    conversation_id: str | None = None
    sandbox_id: str | None = None
    result: dict[str, Any] = {"status": "started", **preflight}
    try:
        start_task = client.start_conversation(
            prompt=PROMPT,
            title="Enterprise native TaskTool capability check",
            repository=None,
            branch=None,
            model=args.model,
        )
        ready = client.poll_start_task(
            str(start_task["id"]),
            timeout_seconds=600,
            poll_seconds=5,
        )
        conversation_id = str(ready["app_conversation_id"])
        terminal, terminal_events, recovered = client.wait_for_terminal(
            conversation_id,
            timeout_seconds=args.timeout,
            poll_seconds=10,
        )
        sandbox_id = terminal.get("sandbox_id")
        response, events = client.final_response(
            conversation_id,
            initial_events=terminal_events,
        )
        event_summary = summarize_events(events)
        metrics = terminal.get("metrics") or {}
        result = {
            "status": (
                "passed"
                if event_summary["task_tool_advertised"]
                and event_summary["task_actions"] == 1
                and event_summary["task_observations"] == 1
                else "unsupported"
            ),
            **preflight,
            "start_task_id": start_task["id"],
            "conversation_id": conversation_id,
            "sandbox_id": sandbox_id,
            "execution_status": terminal.get("execution_status"),
            "terminal_status_recovered": recovered,
            "wall_seconds": round(time.monotonic() - started, 3),
            "model_cost": metrics.get("accumulated_cost"),
            "final_contract_present": (
                "status: done" in response
                and "delegated: yes" in response
                and "ENTERPRISE-TASKTOOL-20260727" in response
            ),
            **event_summary,
        }
    except Exception as exc:
        result = {
            **result,
            "status": "failed",
            "conversation_id": conversation_id,
            "sandbox_id": sandbox_id,
            "error_type": type(exc).__name__,
            "wall_seconds": round(time.monotonic() - started, 3),
        }
    finally:
        if conversation_id and not sandbox_id:
            try:
                sandbox_id = client.get_conversation(conversation_id).get("sandbox_id")
                result["sandbox_id"] = sandbox_id
            except Exception:
                pass
        if sandbox_id:
            try:
                paused = client.pause_sandbox(str(sandbox_id))
                result["cleanup_status"] = paused.get("status")
            except Exception as exc:
                result["cleanup_status"] = f"failed:{type(exc).__name__}"
        try:
            result["capacity_after"] = client.capacity_snapshot(
                runtime_limit=10,
                launch_lock_at=7,
            )
        except Exception:
            result["capacity_after"] = "unavailable"

    write_result(result, args.output)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

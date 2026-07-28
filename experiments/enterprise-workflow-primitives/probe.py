#!/usr/bin/env python3
"""Bounded live probe for reusable OpenHands Enterprise workflow primitives."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_lab.enterprise_events import wait_for_terminal_websocket
from research_lab.openhands import (
    OpenHandsClient,
    configured_api_key,
    configured_base_url,
    sanitize_metadata,
)


def load_env_file(path: Path | None) -> None:
    if path is None:
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key.replace("_", "").isalnum():
            os.environ.setdefault(key, value.strip().strip("'").strip('"'))


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(sanitize_metadata(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def phase(
    result: dict[str, Any],
    name: str,
    *,
    status: str,
    detail: dict[str, Any] | None = None,
) -> None:
    result["phases"][name] = {
        **(sanitize_metadata(detail or {})),
        "status": status,
    }


def delete_probe_resources(
    client: OpenHandsClient,
    conversation_id: str,
    sandbox_id: str,
) -> dict[str, Any]:
    if conversation_id and client.get_conversation(conversation_id):
        client.delete_conversation(conversation_id)
    remaining = client.get_sandbox(sandbox_id) if sandbox_id else {}
    remaining_status = str(remaining.get("status") or "").upper()
    if remaining and remaining_status not in {"MISSING", "DELETED"}:
        client.delete_sandbox(sandbox_id)
        return {
            "conversation_deleted": bool(conversation_id),
            "sandbox_cleanup": "explicit_delete",
        }
    return {
        "conversation_deleted": bool(conversation_id),
        "sandbox_cleanup": "conversation_delete",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-capacity", type=int, default=10)
    parser.add_argument("--launch-lock-at", type=int, default=7)
    parser.add_argument("--start-timeout", type=int, default=600)
    parser.add_argument("--execution-timeout", type=int, default=300)
    parser.add_argument("--tag-timeout", type=int, default=30)
    parser.add_argument(
        "--cleanup",
        choices=("pause", "delete"),
        default="pause",
    )
    parser.add_argument("--skip-websocket", action="store_true")
    parser.add_argument("--live", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.live:
        raise SystemExit("refusing to create a sandbox without --live")
    load_env_file(args.env_file)
    client = OpenHandsClient(
        configured_base_url(args.base_url),
        configured_api_key(),
    )
    started_at = datetime.now(UTC)
    attempt_id = started_at.strftime("%Y%m%dT%H%M%SZ")
    result: dict[str, Any] = {
        "probe": "enterprise-workflow-primitives",
        "target": client.base_url,
        "tested_product_version": "0.24.0",
        "started_at": started_at.isoformat(),
        "cleanup_mode": args.cleanup,
        "phases": {},
    }
    sandbox_id = ""
    conversation_id = ""
    cleanup_complete = False
    try:
        capacity = client.capacity_snapshot(
            runtime_limit=args.runtime_capacity,
            launch_lock_at=args.launch_lock_at,
        )
        if not capacity["launch_allowed"]:
            phase(result, "capacity_gate", status="failed", detail=capacity)
            return 2
        phase(result, "capacity_gate", status="passed", detail=capacity)

        sandbox = client.start_sandbox()
        sandbox_id = str(sandbox["id"])
        phase(
            result,
            "sandbox_create",
            status="passed",
            detail={"sandbox_id": sandbox_id},
        )
        running = client.poll_sandbox(
            sandbox_id,
            timeout_seconds=args.start_timeout,
        )
        phase(
            result,
            "sandbox_ready",
            status="passed",
            detail={
                "sandbox_id": sandbox_id,
                "sandbox_status": running.get("status"),
            },
        )

        start = client.start_conversation(
            prompt=(
                'Return exactly {"status":"ok","message":'
                '"workflow primitives probe"} with no markdown. Do not use tools.'
            ),
            title=f"Workflow primitives probe {attempt_id}",
            repository=None,
            branch=None,
            model=None,
            sandbox_id=sandbox_id,
        )
        start_task_id = str(start["id"])
        ready = client.poll_start_task(
            start_task_id,
            timeout_seconds=args.start_timeout,
            poll_seconds=2,
        )
        conversation_id = str(ready["app_conversation_id"])
        attached_sandbox = str(ready.get("sandbox_id") or "")
        if attached_sandbox != sandbox_id:
            raise RuntimeError(
                f"conversation attached to {attached_sandbox}, expected {sandbox_id}"
            )
        phase(
            result,
            "explicit_sandbox_attach",
            status="passed",
            detail={
                "start_task_id": start_task_id,
                "conversation_id": conversation_id,
                "sandbox_id": sandbox_id,
            },
        )

        requested_tags = {
            "campaignid": "workflowprimitives",
            "taskid": "compatibilityprobe",
            "attemptid": attempt_id.lower(),
            "controllerid": "externalprobe",
        }
        observed_agent_tags = client.patch_agent_tags(
            conversation_id,
            requested_tags,
        )
        deadline = time.monotonic() + args.tag_timeout
        observed_cloud_tags: dict[str, str] = {}
        while time.monotonic() < deadline:
            record = client.get_conversation(conversation_id)
            observed_cloud_tags = dict(record.get("tags") or {})
            if all(
                observed_cloud_tags.get(key) == value
                for key, value in requested_tags.items()
            ):
                break
            time.sleep(1)
        if not all(
            observed_cloud_tags.get(key) == value
            for key, value in requested_tags.items()
        ):
            raise RuntimeError("agent tags did not converge to the app record")
        phase(
            result,
            "conversation_tags",
            status="passed",
            detail={
                "requested": requested_tags,
                "agent_observed": observed_agent_tags,
                "app_observed": observed_cloud_tags,
            },
        )

        server_info = client.get_agent_server_info(conversation_id)
        phase(
            result,
            "server_idle_signal",
            status=(
                "passed"
                if isinstance(server_info.get("idle_time"), (int, float))
                else "unsupported"
            ),
            detail={
                "idle_time_present": isinstance(
                    server_info.get("idle_time"),
                    (int, float),
                ),
                "runtime_idle_timeout_seconds": server_info.get(
                    "runtime_idle_timeout_seconds"
                ),
            },
        )

        if args.skip_websocket:
            phase(result, "websocket_terminal", status="skipped")
        else:
            conversation_url, agent_headers = client.agent_connection(
                conversation_id
            )
            ws_result = asyncio.run(
                wait_for_terminal_websocket(
                    conversation_url,
                    agent_headers["X-Session-API-Key"],
                    timeout_seconds=args.execution_timeout,
                )
            )
            terminal_status = ws_result.pop("status", None)
            phase(
                result,
                "websocket_terminal",
                status="passed",
                detail={
                    "terminal_status": terminal_status,
                    **ws_result,
                },
            )

        record, events, recovered = client.wait_for_terminal(
            conversation_id,
            timeout_seconds=args.execution_timeout,
            poll_seconds=2,
        )
        final_text, final_events = client.final_response(
            conversation_id,
            initial_events=events,
        )
        try:
            contract = json.loads(final_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("worker response was not the expected JSON") from exc
        if contract != {
            "status": "ok",
            "message": "workflow primitives probe",
        }:
            raise RuntimeError("worker response did not match the probe contract")
        phase(
            result,
            "rest_reconciliation",
            status="passed",
            detail={
                "execution_status": record.get("execution_status"),
                "terminal_recovered_from_events": recovered,
                "event_count": len(final_events),
            },
        )
        latest_record = client.get_conversation(conversation_id)
        metrics = latest_record.get("metrics")
        phase(
            result,
            "conversation_metrics",
            status="passed" if isinstance(metrics, dict) else "unsupported",
            detail={"metrics": metrics if isinstance(metrics, dict) else None},
        )

        if args.cleanup == "pause":
            paused = client.pause_sandbox(sandbox_id)
            phase(
                result,
                "cleanup",
                status="passed",
                detail={
                    "mode": "pause",
                    "sandbox_status": paused.get("status"),
                },
            )
        else:
            cleanup_detail = delete_probe_resources(
                client,
                conversation_id,
                sandbox_id,
            )
            phase(
                result,
                "cleanup",
                status="passed",
                detail={
                    "mode": "delete",
                    **cleanup_detail,
                },
            )
        cleanup_complete = True
        result["status"] = "passed"
        return 0
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc)[:1000],
        }
        return 1
    finally:
        if sandbox_id and not cleanup_complete:
            try:
                cleanup_detail = delete_probe_resources(
                    client,
                    conversation_id,
                    sandbox_id,
                )
                phase(
                    result,
                    "emergency_cleanup",
                    status="passed",
                    detail=cleanup_detail,
                )
            except Exception as cleanup_error:
                phase(
                    result,
                    "emergency_cleanup",
                    status="failed",
                    detail={
                        "type": type(cleanup_error).__name__,
                        "message": str(cleanup_error)[:500],
                    },
                )
        result["conversation_id"] = conversation_id or None
        result["sandbox_id"] = sandbox_id or None
        result["finished_at"] = datetime.now(UTC).isoformat()
        write_result(args.output, result)
        print(
            json.dumps(
                {
                    "status": result.get("status"),
                    "conversation_id": conversation_id or None,
                    "sandbox_id": sandbox_id or None,
                    "phases": {
                        name: value.get("status")
                        for name, value in result["phases"].items()
                    },
                    "output": str(args.output),
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    sys.exit(main())

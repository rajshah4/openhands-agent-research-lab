#!/usr/bin/env python3
"""Compare native TaskToolSet execution with first-class Canvas conversations."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TERMINAL = {"finished", "error", "stuck", "stopped"}
CASES = (
    {
        "case_id": "scheduler",
        "path": "src/research_lab/scheduler.py",
        "symbols": ("RoundRobinPolicy", "ManagedPolicy", "policy_for"),
    },
    {
        "case_id": "store",
        "path": "src/research_lab/store.py",
        "symbols": ("FileResearchStore", "controller_lock", "_atomic_write_text"),
    },
    {
        "case_id": "runner",
        "path": "src/research_lab/runner.py",
        "symbols": (
            "CampaignRunner",
            "_reconcile_incomplete_attempts",
            "_record_successful_execution",
        ),
    },
    {
        "case_id": "canvas",
        "path": "src/research_lab/canvas.py",
        "symbols": ("CanvasClient", "capacity_snapshot", "wait_for_terminal"),
    },
)


class ExperimentError(RuntimeError):
    pass


def request_json(
    method: str,
    url: str,
    *,
    key: str,
    payload: dict[str, Any] | None = None,
    expose_encrypted: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    headers = {"Accept": "application/json", "X-Session-API-Key": key}
    if expose_encrypted:
        headers["X-Expose-Secrets"] = "encrypted"
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    try:
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise ExperimentError(f"{method} {url} returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise ExperimentError(f"{method} {url} failed") from exc
    return json.loads(body) if body else {}


def load_key(path: Path) -> str:
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ExperimentError("Canvas session key file is empty")
    return value


def clean_agent_settings(settings: dict[str, Any], *, concurrency: int, task_tool: bool) -> dict[str, Any]:
    agent = dict(settings.get("agent_settings") or {})
    agent.pop("schema_version", None)
    agent.pop("mcp_config", None)
    agent["tool_concurrency_limit"] = concurrency
    tools = [
        {"name": "terminal", "params": {}},
        {"name": "file_editor", "params": {}},
        {"name": "task_tracker", "params": {}},
    ]
    if task_tool:
        tools.append({"name": "task_tool_set", "params": {}})
    agent["tools"] = tools
    context = dict(agent.get("agent_context") or {})
    context.update(
        {
            "load_public_skills": False,
            "load_user_skills": False,
            "load_project_skills": False,
        }
    )
    agent["agent_context"] = context
    return agent


def case_prompt(
    case: dict[str, Any], *, inject_contract_failure: bool = False
) -> str:
    if inject_contract_failure:
        return (
            f"CASE_ID={case['case_id']}\n"
            "This is an intentional contract-failure injection. Do not inspect files or call "
            f"tools. Return exactly `INTENTIONAL_FAILURE {case['case_id']}` and stop."
        )
    symbols = ", ".join(case["symbols"])
    return (
        f"CASE_ID={case['case_id']}\n"
        f"Inspect only `{case['path']}`. Confirm where these symbols are defined or used: {symbols}. "
        "Explain the module's responsibility and identify one concrete operational risk or limitation. "
        "Do not edit files. Finish with one compact JSON object containing case_id, path, "
        "symbols_found (an array), responsibility, risk, and evidence (an array of at least two "
        "path:line references)."
    )


def parent_prompt(mode: str, *, failure_case: str | None = None) -> str:
    instructions = "\n\n".join(
        f"Delegation {index + 1}:\n"
        f"{case_prompt(case, inject_contract_failure=case['case_id'] == failure_case)}"
        for index, case in enumerate(CASES)
    )
    return (
        f"Run a matched {mode} native TaskToolSet experiment. In your next assistant step, issue "
        "exactly four `task` tool calls, one for each delegation below, all with "
        "`subagent_type=\"code-explorer\"`. Submit all four calls in the same assistant response. "
        "Do not inspect the files yourself and do not create conversations through HTTP. The tool "
        "executor controls whether the four calls run sequentially or concurrently. After every "
        "child returns, finish with a compact JSON object containing status, mode, completed_cases, "
        "task_ids, and summary. Do not call any other tool.\n\n"
        f"{instructions}"
    )


def build_payload(
    settings: dict[str, Any],
    *,
    prompt: str,
    workspace: Path,
    concurrency: int,
    task_tool: bool,
) -> dict[str, Any]:
    conversation = settings.get("conversation_settings") or {}
    return {
        "secrets_encrypted": True,
        "agent_settings": clean_agent_settings(
            settings, concurrency=concurrency, task_tool=task_tool
        ),
        "workspace": {
            "kind": "LocalWorkspace",
            "working_dir": str(workspace.resolve()),
        },
        "confirmation_policy": {"kind": "NeverConfirm"},
        "max_iterations": min(int(conversation.get("max_iterations") or 100), 40),
        "stuck_detection": True,
        "autotitle": True,
        "worktree": False,
        "initial_message": {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
            "run": True,
        },
    }


def create_conversation(
    base: str,
    key: str,
    settings: dict[str, Any],
    *,
    prompt: str,
    workspace: Path,
    concurrency: int,
    task_tool: bool,
) -> str:
    response = request_json(
        "POST",
        f"{base}/api/conversations",
        key=key,
        payload=build_payload(
            settings,
            prompt=prompt,
            workspace=workspace,
            concurrency=concurrency,
            task_tool=task_tool,
        ),
    )
    conversation_id = str(response.get("id") or "")
    if not conversation_id:
        raise ExperimentError("Canvas did not return a conversation ID")
    return conversation_id


def wait_for_terminal(base: str, key: str, conversation_id: str, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        record = request_json(
            "GET", f"{base}/api/conversations/{conversation_id}", key=key
        )
        if record.get("execution_status") in TERMINAL:
            return record
        time.sleep(2)
    raise ExperimentError(f"Conversation {conversation_id} timed out")


def events(base: str, key: str, conversation_id: str) -> list[dict[str, Any]]:
    response = request_json(
        "GET",
        f"{base}/api/conversations/{conversation_id}/events/search?limit=100&sort_order=TIMESTAMP",
        key=key,
    )
    return list(response.get("items") or [])


def final_response(base: str, key: str, conversation_id: str) -> str:
    response = request_json(
        "GET",
        f"{base}/api/conversations/{conversation_id}/agent_final_response",
        key=key,
    )
    value = response.get("final_response") or response.get("response") or ""
    return str(value)


def parse_timestamp(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def record_wall_seconds(record: dict[str, Any]) -> float:
    return (
        parse_timestamp(str(record["updated_at"]))
        - parse_timestamp(str(record["created_at"]))
    ).total_seconds()


def cost_summary(record: dict[str, Any]) -> dict[str, Any]:
    scopes = (record.get("stats") or {}).get("usage_to_metrics") or {}
    by_scope = {
        name: round(float(metrics.get("accumulated_cost") or 0), 8)
        for name, metrics in scopes.items()
    }
    calls = sum(len(metrics.get("costs") or []) for metrics in scopes.values())
    return {
        "by_scope": by_scope,
        "total": round(sum(by_scope.values()), 8),
        "model_calls": calls,
    }


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text") or "")
            for item in content
            if isinstance(item, dict)
        )
    return ""


def validate_case(case: dict[str, Any], text: str) -> dict[str, Any]:
    missing = [
        expected
        for expected in (case["path"], *case["symbols"])
        if expected not in text
    ]
    case_id_present = case["case_id"] in text
    return {
        "case_id": case["case_id"],
        "valid": not missing,
        "contract_valid": case_id_present and not missing,
        "case_id_present": case_id_present,
        "missing": missing,
    }


def task_event_summary(all_events: list[dict[str, Any]]) -> dict[str, Any]:
    actions = [
        event
        for event in all_events
        if event.get("kind") == "ActionEvent"
        and (event.get("action") or {}).get("kind") == "TaskAction"
    ]
    observations = [
        event
        for event in all_events
        if event.get("kind") == "ObservationEvent"
        and (event.get("observation") or {}).get("kind") == "TaskObservation"
    ]
    action_by_case = {
        case["case_id"]: next(
            (
                event
                for event in actions
                if f"CASE_ID={case['case_id']}"
                in str((event.get("action") or {}).get("prompt") or "")
            ),
            None,
        )
        for case in CASES
    }
    validations = []
    for case in CASES:
        action = action_by_case[case["case_id"]]
        match = next(
            (
                event
                for event in observations
                if action and event.get("action_id") == action.get("id")
            ),
            None,
        )
        validations.append(
            validate_case(
                case,
                content_text((match.get("observation") or {}).get("content"))
                if match
                else "",
            )
        )
    action_times = [parse_timestamp(str(event["timestamp"])) for event in actions]
    observation_times = [
        parse_timestamp(str(event["timestamp"])) for event in observations
    ]
    return {
        "task_actions": len(actions),
        "task_observations": len(observations),
        "task_ids": [
            (event.get("observation") or {}).get("task_id") for event in observations
        ],
        "child_validations": validations,
        "all_children_valid": all(item["valid"] for item in validations),
        "all_contracts_valid": all(
            item["contract_valid"] for item in validations
        ),
        "first_action_to_last_observation_seconds": round(
            (max(observation_times) - min(action_times)).total_seconds(), 3
        )
        if action_times and observation_times
        else None,
        "action_timestamp_spread_seconds": round(
            (max(action_times) - min(action_times)).total_seconds(), 3
        )
        if len(action_times) > 1
        else 0.0,
    }


def run_parent_mode(
    base: str,
    key: str,
    settings: dict[str, Any],
    workspace: Path,
    *,
    mode: str,
    concurrency: int,
    timeout_seconds: int,
    failure_case: str | None,
) -> dict[str, Any]:
    started = time.monotonic()
    conversation_id = create_conversation(
        base,
        key,
        settings,
        prompt=parent_prompt(mode, failure_case=failure_case),
        workspace=workspace,
        concurrency=concurrency,
        task_tool=True,
    )
    record = wait_for_terminal(base, key, conversation_id, timeout_seconds)
    trajectory = events(base, key, conversation_id)
    final = final_response(base, key, conversation_id)
    task_summary = task_event_summary(trajectory)
    result = {
        "mode": mode,
        "injected_contract_failure": failure_case,
        "conversation_ids": [conversation_id],
        "execution_statuses": [record.get("execution_status")],
        "harness_wall_seconds": round(time.monotonic() - started, 3),
        "record_wall_seconds": round(record_wall_seconds(record), 3),
        "cost": cost_summary(record),
        "final_contract_present": all(
            token in final
            for token in ("status", "completed_cases", "task_ids", "summary")
        ),
        **task_summary,
    }
    if failure_case:
        result["expected_failure_observed"] = all(
            item["valid"] == (item["case_id"] != failure_case)
            for item in task_summary["child_validations"]
        )
    return result


def run_external_mode(
    base: str,
    key: str,
    settings: dict[str, Any],
    workspace: Path,
    *,
    timeout_seconds: int,
    failure_case: str | None,
) -> dict[str, Any]:
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        creation_futures = [
            pool.submit(
                create_conversation,
                base,
                key,
                settings,
                prompt=case_prompt(
                    case, inject_contract_failure=case["case_id"] == failure_case
                ),
                workspace=workspace,
                concurrency=1,
                task_tool=False,
            )
            for case in CASES
        ]
        conversation_ids = [future.result() for future in creation_futures]
        wait_futures = [
            pool.submit(wait_for_terminal, base, key, conversation_id, timeout_seconds)
            for conversation_id in conversation_ids
        ]
        records = [future.result() for future in wait_futures]

    finals = [
        final_response(base, key, conversation_id)
        for conversation_id in conversation_ids
    ]
    validations = [
        validate_case(case, final)
        for case, final in zip(CASES, finals, strict=True)
    ]
    costs = [cost_summary(record) for record in records]
    result = {
        "mode": "external",
        "injected_contract_failure": failure_case,
        "conversation_ids": conversation_ids,
        "execution_statuses": [record.get("execution_status") for record in records],
        "harness_wall_seconds": round(time.monotonic() - started, 3),
        "record_wall_seconds": [
            round(record_wall_seconds(record), 3) for record in records
        ],
        "cost": {
            "by_conversation": [cost["total"] for cost in costs],
            "total": round(sum(cost["total"] for cost in costs), 8),
            "model_calls": sum(cost["model_calls"] for cost in costs),
        },
        "task_actions": 0,
        "task_observations": 0,
        "child_validations": validations,
        "all_children_valid": all(item["valid"] for item in validations),
        "all_contracts_valid": all(
            item["contract_valid"] for item in validations
        ),
        "first_action_to_last_observation_seconds": None,
        "action_timestamp_spread_seconds": None,
    }
    if failure_case:
        result["expected_failure_observed"] = all(
            item["valid"] == (item["case_id"] != failure_case)
            for item in validations
        )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--base", default="http://127.0.0.1:18000")
    parser.add_argument(
        "--key-file",
        type=Path,
        default=Path("/Users/rajiv.shah/.openhands/agent-canvas/api-key.txt"),
    )
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--mode", choices=("sequential", "parallel", "external"), required=True
    )
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument(
        "--inject-contract-failure",
        choices=tuple(case["case_id"] for case in CASES),
        help="Make one child return a known-invalid contract for failure-boundary testing.",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.live:
        print("Refusing to make LLM calls without --live", file=sys.stderr)
        return 2
    if not args.workspace.is_dir():
        print("Workspace does not exist", file=sys.stderr)
        return 2
    key = load_key(args.key_file)
    server = request_json("GET", f"{args.base}/server_info", key=key)
    usable = set(server.get("usable_tools") or [])
    if args.mode != "external" and not {"task", "task_tool_set"} & usable:
        print("Agent Server does not advertise TaskToolSet", file=sys.stderr)
        return 2
    settings = request_json(
        "GET",
        f"{args.base}/api/settings",
        key=key,
        expose_encrypted=True,
    )
    if args.mode == "external":
        result = run_external_mode(
            args.base,
            key,
            settings,
            args.workspace,
            timeout_seconds=args.timeout_seconds,
            failure_case=args.inject_contract_failure,
        )
    else:
        result = run_parent_mode(
            args.base,
            key,
            settings,
            args.workspace,
            mode=args.mode,
            concurrency=1 if args.mode == "sequential" else 4,
            timeout_seconds=args.timeout_seconds,
            failure_case=args.inject_contract_failure,
        )
    result["server"] = {
        "version": server.get("version"),
        "sdk_version": server.get("sdk_version"),
        "tools_version": server.get("tools_version"),
    }
    result["completed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    if args.inject_contract_failure:
        return 0 if result.get("expected_failure_observed") else 1
    return 0 if result.get("all_children_valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())

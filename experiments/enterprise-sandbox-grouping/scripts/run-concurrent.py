#!/usr/bin/env python3
"""Run a queued, validated OpenHands workload in a rate-limited sandbox pool."""

from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import threading
import time
import urllib.parse
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from research_lab.cli import _load_env_file
from research_lab.domain import CampaignSpec
from research_lab.openhands import (
    OpenHandsClient,
    configured_api_key,
    request_json,
)
from research_lab.runner import CampaignRunner
from research_lab.scheduler import policy_for
from research_lab.store import FileResearchStore
from research_lab.workers import OpenHandsWorker


class PacedRequester:
    """Pace controller requests; OpenHandsClient owns bounded retries."""

    def __init__(self, interval_seconds: float):
        self.interval_seconds = interval_seconds
        self._lock = threading.Lock()
        self._next_request_at = 0.0

    def __call__(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
        timeout: int = 60,
    ) -> Any:
        with self._lock:
            now = time.monotonic()
            delay = max(self._next_request_at - now, 0.0)
            if delay:
                time.sleep(delay)
            self._next_request_at = time.monotonic() + self.interval_seconds
        return request_json(
            method,
            url,
            headers,
            body=body,
            timeout=timeout,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument(
        "--base-url",
        default="https://app.replicated.rajistics.com",
    )
    parser.add_argument(
        "--repository",
        default="rajshah4/openhands-agent-research-lab",
    )
    parser.add_argument(
        "--no-repository",
        action="store_true",
        help="run prompt-contained tasks without mounting a Git repository",
    )
    parser.add_argument("--branch", default="main")
    parser.add_argument(
        "--model",
        help="explicit OpenHands model identifier for matched live comparisons",
    )
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument(
        "--workload-size",
        type=int,
        help=(
            "total queued tasks; cycles through the campaign with unique task "
            "IDs when larger than --concurrency"
        ),
    )
    parser.add_argument(
        "--dispatch-limit",
        type=int,
        help="maximum simultaneously executing agents; defaults to concurrency",
    )
    parser.add_argument("--expected-sandboxes", type=int, default=1)
    parser.add_argument(
        "--require-grouping-strategy",
        choices=("NO_GROUPING", "FEWEST_CONVERSATIONS"),
        help="refuse the run unless the authenticated user has this strategy",
    )
    parser.add_argument("--request-interval", type=float, default=0.75)
    parser.add_argument("--seed-ready-timeout", type=int, default=180)
    parser.add_argument("--start-timeout", type=int, default=600)
    parser.add_argument("--execution-timeout", type=int, default=900)
    parser.add_argument("--poll-seconds", type=int, default=2)
    parser.add_argument(
        "--defer-sandbox-cleanup",
        action="store_true",
        help=(
            "Leave the grouped sandbox for an outer automation with "
            "keep_alive=false to clean up after this controller exits"
        ),
    )
    parser.add_argument("--live", action="store_true")
    return parser.parse_args()


def timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def lifecycle_files(root: Path, kind: str) -> list[Path]:
    return sorted(root.glob(f"*/runs/*/lifecycle/*/*-{kind}.json"))


def load_lifecycle(root: Path, kind: str) -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in lifecycle_files(root, kind)
    ]


def max_observed_concurrency(root: Path) -> int:
    ready_by_attempt = {
        item["attempt_id"]: timestamp(item["recorded_at"])
        for item in load_lifecycle(root, "conversation_ready")
    }
    terminal_by_attempt = {
        item["attempt_id"]: timestamp(item["recorded_at"])
        for item in load_lifecycle(root, "conversation_terminal")
    }
    points: list[tuple[datetime, int]] = []
    for attempt_id, ready_at in ready_by_attempt.items():
        terminal_at = terminal_by_attempt.get(attempt_id)
        if terminal_at is None:
            continue
        points.extend(((ready_at, 1), (terminal_at, -1)))
    active = 0
    maximum = 0
    for _, delta in sorted(points, key=lambda item: (item[0], item[1])):
        active += delta
        maximum = max(maximum, active)
    return maximum


def sandbox_ids_from_lifecycle(root: Path) -> list[str]:
    return sorted(
        {
            str(item["payload"]["sandbox_id"])
            for kind in ("conversation_ready", "conversation_start_failed")
            for item in load_lifecycle(root, kind)
            if item.get("payload", {}).get("sandbox_id")
        }
    )


def usage_metrics(attempt: dict[str, Any]) -> dict[str, Any]:
    metadata = attempt.get("metadata") or {}
    snapshot = metadata.get("conversation_snapshot") or {}
    metrics = snapshot.get("metrics") or {}
    return metrics if isinstance(metrics, dict) else {}


def attempt_duration_seconds(attempt: dict[str, Any]) -> float | None:
    started_at = attempt.get("started_at")
    finished_at = attempt.get("finished_at")
    if not started_at or not finished_at:
        return None
    return (timestamp(str(finished_at)) - timestamp(str(started_at))).total_seconds()


def physical_runtime(attempt: dict[str, Any]) -> str | None:
    metadata = attempt.get("metadata") or {}
    snapshot = metadata.get("conversation_snapshot") or {}
    conversation_url = str(snapshot.get("conversation_url") or "")
    hostname = urllib.parse.urlsplit(conversation_url).hostname or ""
    suffix = ".runtime."
    if suffix not in hostname:
        return None
    return f"runtime-{hostname.split(suffix, 1)[0]}"


def main() -> int:
    args = parse_args()
    if not args.live:
        raise ValueError("this experiment creates real conversations; pass --live")
    if args.request_interval < 0.65:
        raise ValueError(
            "--request-interval must be at least 0.65 seconds to stay below "
            "the observed 100-request-per-minute API limit"
        )
    if not 2 <= args.concurrency <= 6:
        raise ValueError("--concurrency must be between 2 and 6")
    workload_size = args.workload_size or args.concurrency
    if not args.concurrency <= workload_size <= 100:
        raise ValueError(
            "--workload-size must be between --concurrency and 100"
        )
    dispatch_limit = args.dispatch_limit or args.concurrency
    if not 1 <= dispatch_limit <= workload_size:
        raise ValueError(
            "--dispatch-limit must be between 1 and --workload-size"
        )
    if not 1 <= args.expected_sandboxes <= workload_size:
        raise ValueError(
            "--expected-sandboxes must be between 1 and --workload-size"
        )

    _load_env_file(args.env_file)
    base_campaign = CampaignSpec.from_path(args.campaign.resolve())
    selected_repository = None if args.no_repository else args.repository
    selected_branch = None if args.no_repository else args.branch
    base_campaign = replace(
        base_campaign,
        repository=selected_repository,
        branch=selected_branch,
        model=args.model or base_campaign.model,
        attempt_budget=1,
        policy="managed",
    )
    source_tasks = base_campaign.tasks[: args.concurrency]
    if len(source_tasks) != args.concurrency:
        raise ValueError(
            f"campaign has {len(base_campaign.tasks)} tasks but "
            f"--concurrency is {args.concurrency}"
        )
    scaled_tasks = tuple(
        replace(
            source_tasks[index % len(source_tasks)],
            id=(
                f"{source_tasks[index % len(source_tasks)].id}"
                f"-scale-{index + 1:03d}"
            ),
        )
        for index in range(workload_size)
    )
    base_campaign = replace(base_campaign, tasks=scaled_tasks)
    tasks = {task.id: task for task in scaled_tasks}
    task_order = [task.id for task in scaled_tasks]

    args.store.mkdir(parents=True, exist_ok=True)
    limiter = PacedRequester(args.request_interval)
    client = OpenHandsClient(
        args.base_url,
        configured_api_key(),
        requester=limiter,
    )

    user_settings = client.preflight()
    grouping_strategy = str(
        user_settings.get("sandbox_grouping_strategy") or ""
    )
    if (
        args.require_grouping_strategy
        and grouping_strategy != args.require_grouping_strategy
    ):
        raise RuntimeError(
            f"sandbox grouping strategy is {grouping_strategy!r}, expected "
            f"{args.require_grouping_strategy!r}"
        )
    capacity = client.capacity_snapshot(runtime_limit=10, launch_lock_at=7)
    if not capacity["launch_allowed"]:
        raise RuntimeError("OpenHands capacity gate is closed")

    def run_task(task_id: str) -> dict[str, Any]:
        campaign = replace(base_campaign, tasks=(tasks[task_id],))
        store = FileResearchStore(args.store / task_id)
        worker = OpenHandsWorker(
            client,
            start_timeout_seconds=args.start_timeout,
            execution_timeout_seconds=args.execution_timeout,
            poll_seconds=args.poll_seconds,
            pause_after_attempt=grouping_strategy == "NO_GROUPING",
            runtime_limit=10,
            launch_lock_at=7,
        )
        run_id, _ = CampaignRunner(
            store=store,
            worker=worker,
            scheduler=policy_for("managed"),
        ).run(campaign)
        attempts = store.list_attempts(run_id)
        return attempts[0] if attempts else {}

    started = time.monotonic()
    futures: dict[str, Future[dict[str, Any]]] = {}
    results: dict[str, dict[str, Any]] = {}
    pause_results: dict[str, str] = {}
    pause_errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=dispatch_limit) as executor:
        seed_id = task_order[0]
        futures[seed_id] = executor.submit(run_task, seed_id)
        deadline = time.monotonic() + args.seed_ready_timeout
        seed_ready = False
        while time.monotonic() < deadline:
            if lifecycle_files(args.store, "conversation_ready"):
                seed_ready = True
                break
            if futures[seed_id].done():
                results[seed_id] = futures[seed_id].result()
                break
            time.sleep(0.5)
        else:
            raise TimeoutError("timed out waiting for seed conversation readiness")

        if seed_ready:
            for task_id in task_order[1:]:
                futures[task_id] = executor.submit(run_task, task_id)
            for task_id, future in futures.items():
                results[task_id] = future.result()

    controller_wall_seconds = time.monotonic() - started
    sandbox_ids = sandbox_ids_from_lifecycle(args.store)
    if not args.defer_sandbox_cleanup:
        for sandbox_id in sandbox_ids:
            try:
                current = client.get_sandbox(sandbox_id)
                if str(current.get("status", "")).upper() == "PAUSED":
                    pause_results[sandbox_id] = "PAUSED"
                else:
                    paused = client.pause_sandbox(sandbox_id)
                    pause_results[sandbox_id] = str(paused.get("status"))
            except Exception as exc:
                pause_errors[sandbox_id] = f"{type(exc).__name__}: {exc}"
    if True:
        durations = [
            duration
            for item in results.values()
            if (duration := attempt_duration_seconds(item)) is not None
        ]
        started_at = [
            timestamp(str(item["started_at"]))
            for item in results.values()
            if item.get("started_at")
        ]
        finished_at = [
            timestamp(str(item["finished_at"]))
            for item in results.values()
            if item.get("finished_at")
        ]
        attempt_batch_wall_seconds = (
            (max(finished_at) - min(started_at)).total_seconds()
            if started_at and finished_at
            else None
        )
        metrics = [usage_metrics(item) for item in results.values()]
        token_usage = [
            item.get("accumulated_token_usage") or {}
            for item in metrics
        ]
        summary = {
            "schema_version": 1,
            "campaign": base_campaign.id,
            "model": base_campaign.model,
            "repository": base_campaign.repository,
            "branch": base_campaign.branch,
            "sandbox_grouping_strategy": grouping_strategy,
            "workload_size": workload_size,
            "source_task_count": len(source_tasks),
            "dispatch_limit": dispatch_limit,
            "expected_sandboxes": args.expected_sandboxes,
            "tasks": task_order,
            "attempts": len(results),
            "valid": sum(
                bool(item.get("validation", {}).get("valid"))
                for item in results.values()
            ),
            "failed": sum(
                item.get("outcome") != "completed" for item in results.values()
            ),
            "sandbox_ids": sandbox_ids,
            "max_observed_concurrency": max_observed_concurrency(args.store),
            "rate_limit_retries": client.retry_metrics()["rate_limit"],
            "transient_auth_retries": client.retry_metrics()["transient_auth"],
            "server_retries": client.retry_metrics()["server"],
            "transport_retries": client.retry_metrics()["transport"],
            "controller_wall_seconds": round(controller_wall_seconds, 3),
            "attempt_batch_wall_seconds": (
                round(attempt_batch_wall_seconds, 3)
                if attempt_batch_wall_seconds is not None
                else None
            ),
            "throughput_tasks_per_hour": (
                round(len(results) * 3600 / attempt_batch_wall_seconds, 2)
                if attempt_batch_wall_seconds
                else None
            ),
            "mean_attempt_seconds": (
                round(statistics.mean(durations), 3) if durations else None
            ),
            "median_attempt_seconds": (
                round(statistics.median(durations), 3) if durations else None
            ),
            "maximum_attempt_seconds": (
                round(max(durations), 3) if durations else None
            ),
            "total_cost": round(
                sum(float(item.get("accumulated_cost") or 0) for item in metrics),
                8,
            ),
            "total_prompt_tokens": sum(
                int(item.get("prompt_tokens") or 0) for item in token_usage
            ),
            "total_completion_tokens": sum(
                int(item.get("completion_tokens") or 0) for item in token_usage
            ),
            "observed_models": sorted(
                {
                    str(
                        (item.get("metadata") or {})
                        .get("conversation_snapshot", {})
                        .get("llm_model")
                    )
                    for item in results.values()
                    if (item.get("metadata") or {})
                    .get("conversation_snapshot", {})
                    .get("llm_model")
                }
            ),
            "physical_runtimes": sorted(
                {
                    runtime
                    for item in results.values()
                    if (runtime := physical_runtime(item))
                }
            ),
            "wall_seconds": round(time.monotonic() - started, 3),
            "cleanup_owner": (
                "outer-automation"
                if args.defer_sandbox_cleanup
                else "controller"
            ),
            "pause_results": pause_results,
            "pause_errors": pause_errors,
            "conversations": {
                task_id: {
                    "conversation_id": item.get("conversation", {}).get(
                        "conversation_id"
                    ),
                    "sandbox_id": item.get("conversation", {}).get("sandbox_id"),
                    "outcome": item.get("outcome"),
                    "valid": item.get("validation", {}).get("valid"),
                    "score": item.get("validation", {}).get("score"),
                    "failure": item.get("failure"),
                }
                for task_id, item in results.items()
            },
        }
        (args.store / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(summary, indent=2, sort_keys=True))

    return (
        0
        if (
            summary["valid"] == workload_size
            and len(sandbox_ids) == args.expected_sandboxes
            and not pause_errors
            and (
                args.defer_sandbox_cleanup
                or len(pause_results) == len(sandbox_ids)
            )
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())

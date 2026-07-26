#!/usr/bin/env python3
"""Run two to six validated OpenHands workers in one rate-limited sandbox pool."""

from __future__ import annotations

import argparse
import glob
import json
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from research_lab.cli import _load_env_file
from research_lab.domain import CampaignSpec
from research_lab.openhands import (
    OpenHandsAPIError,
    OpenHandsClient,
    configured_api_key,
    request_json,
)
from research_lab.runner import CampaignRunner
from research_lab.scheduler import policy_for
from research_lab.store import FileResearchStore
from research_lab.workers import OpenHandsWorker


class RateLimitedRequester:
    """Pace all controller requests and retry bounded HTTP 429 responses."""

    def __init__(self, interval_seconds: float, max_429_retries: int = 4):
        self.interval_seconds = interval_seconds
        self.max_429_retries = max_429_retries
        self._lock = threading.Lock()
        self._next_request_at = 0.0
        self.rate_limit_retries = 0

    def __call__(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
        timeout: int = 60,
    ) -> Any:
        for retry in range(self.max_429_retries + 1):
            with self._lock:
                now = time.monotonic()
                delay = max(self._next_request_at - now, 0.0)
                if delay:
                    time.sleep(delay)
                self._next_request_at = time.monotonic() + self.interval_seconds
            try:
                return request_json(
                    method,
                    url,
                    headers,
                    body=body,
                    timeout=timeout,
                )
            except OpenHandsAPIError as exc:
                if "HTTP 429" not in str(exc) or retry >= self.max_429_retries:
                    raise
                self.rate_limit_retries += 1
                time.sleep(min(2**retry, 8))
        raise AssertionError("unreachable")


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
    parser.add_argument("--branch", default="main")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--request-interval", type=float, default=0.25)
    parser.add_argument("--seed-ready-timeout", type=int, default=180)
    parser.add_argument("--start-timeout", type=int, default=600)
    parser.add_argument("--execution-timeout", type=int, default=900)
    parser.add_argument("--poll-seconds", type=int, default=2)
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
            for item in load_lifecycle(root, "conversation_ready")
            if item.get("payload", {}).get("sandbox_id")
        }
    )


def main() -> int:
    args = parse_args()
    if not args.live:
        raise ValueError("this experiment creates real conversations; pass --live")
    if args.request_interval < 0.2:
        raise ValueError("--request-interval must be at least 0.2 seconds")
    if not 2 <= args.concurrency <= 6:
        raise ValueError("--concurrency must be between 2 and 6")

    _load_env_file(args.env_file)
    base_campaign = CampaignSpec.from_path(args.campaign.resolve())
    base_campaign = replace(
        base_campaign,
        repository=args.repository,
        branch=args.branch,
        attempt_budget=1,
        policy="managed",
    )
    tasks = {task.id: task for task in base_campaign.tasks}
    task_order = [
        "color-cycle-7",
        "color-bipartite-8",
        "cover-campus",
        "cover-grid",
        "pack-alpha",
        "pack-beta",
    ][: args.concurrency]
    missing = [task_id for task_id in task_order if task_id not in tasks]
    if missing:
        raise ValueError("campaign is missing tasks: " + ", ".join(missing))

    args.store.mkdir(parents=True, exist_ok=True)
    limiter = RateLimitedRequester(args.request_interval)
    client = OpenHandsClient(
        args.base_url,
        configured_api_key(),
        requester=limiter,
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
            pause_after_attempt=False,
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
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        seed_id = task_order[0]
        futures[seed_id] = executor.submit(run_task, seed_id)
        deadline = time.monotonic() + args.seed_ready_timeout
        while time.monotonic() < deadline:
            if lifecycle_files(args.store, "conversation_ready"):
                break
            if futures[seed_id].done():
                results[seed_id] = futures[seed_id].result()
                raise RuntimeError("seed ended before its conversation became ready")
            time.sleep(0.5)
        else:
            raise TimeoutError("timed out waiting for seed conversation readiness")

        for task_id in task_order[1:]:
            futures[task_id] = executor.submit(run_task, task_id)
        for task_id, future in futures.items():
            results[task_id] = future.result()

    sandbox_ids = sandbox_ids_from_lifecycle(args.store)
    try:
        for sandbox_id in sandbox_ids:
            paused = client.pause_sandbox(sandbox_id)
            pause_results[sandbox_id] = str(paused.get("status"))
    finally:
        summary = {
            "schema_version": 1,
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
            "rate_limit_retries": limiter.rate_limit_retries,
            "wall_seconds": round(time.monotonic() - started, 3),
            "pause_results": pause_results,
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
        if summary["valid"] == args.concurrency and len(sandbox_ids) == 1
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())

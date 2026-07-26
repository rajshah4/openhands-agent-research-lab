#!/usr/bin/env python3
"""Pause named Enterprise sandboxes and verify each final state."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from research_lab.cli import _load_env_file
from research_lab.openhands import (
    OpenHandsAPIError,
    OpenHandsClient,
    configured_api_key,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("sandbox_ids", nargs="+")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument(
        "--base-url",
        default="https://app.replicated.rajistics.com",
    )
    parser.add_argument("--request-interval", type=float, default=3.0)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--live", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.live:
        raise RuntimeError("refusing sandbox mutation without --live")
    _load_env_file(args.env_file)
    client = OpenHandsClient(args.base_url, configured_api_key())
    results: dict[str, str] = {}
    failures: dict[str, str] = {}
    for sandbox_id in dict.fromkeys(args.sandbox_ids):
        for attempt in range(args.retries + 1):
            try:
                current = client.get_sandbox(sandbox_id)
                if str(current.get("status", "")).upper() == "PAUSED":
                    results[sandbox_id] = "PAUSED"
                else:
                    paused = client.pause_sandbox(
                        sandbox_id,
                        poll_seconds=max(int(args.request_interval), 1),
                    )
                    results[sandbox_id] = str(paused.get("status"))
                break
            except OpenHandsAPIError as exc:
                if attempt >= args.retries:
                    failures[sandbox_id] = f"{type(exc).__name__}: {exc}"
                    break
                time.sleep(args.request_interval * (attempt + 1))
        time.sleep(args.request_interval)
    print(
        json.dumps(
            {"pause_results": results, "pause_errors": failures},
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if failures or any(value != "PAUSED" for value in results.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())

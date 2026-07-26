#!/usr/bin/env python3
"""Safely change and verify the current user's sandbox grouping strategy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_lab.cli import _load_env_file
from research_lab.openhands import (
    SANDBOX_GROUPING_STRATEGIES,
    OpenHandsClient,
    configured_api_key,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strategy",
        required=True,
        choices=sorted(SANDBOX_GROUPING_STRATEGIES),
    )
    parser.add_argument("--env-file", type=Path)
    parser.add_argument(
        "--base-url",
        default="https://app.replicated.rajistics.com",
    )
    parser.add_argument("--runtime-limit", type=int, default=10)
    parser.add_argument("--launch-lock-at", type=int, default=7)
    parser.add_argument(
        "--allow-active-sandboxes",
        action="store_true",
        help="override the zero-active-sandbox safety check",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="required acknowledgement for the settings mutation",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.live:
        raise RuntimeError("refusing settings mutation without --live")
    _load_env_file(args.env_file)
    client = OpenHandsClient(args.base_url, configured_api_key())
    before = client.preflight()
    capacity_before = client.capacity_snapshot(
        runtime_limit=args.runtime_limit,
        launch_lock_at=args.launch_lock_at,
    )
    if capacity_before["active"] and not args.allow_active_sandboxes:
        raise RuntimeError(
            "refusing to change grouping while active sandboxes exist; "
            "pause or drain them first"
        )
    observed = client.set_sandbox_grouping_strategy(args.strategy)
    capacity_after = client.capacity_snapshot(
        runtime_limit=args.runtime_limit,
        launch_lock_at=args.launch_lock_at,
    )
    print(
        json.dumps(
            {
                "strategy_before": before.get("sandbox_grouping_strategy"),
                "strategy_after": observed,
                "active_before": capacity_before["active"],
                "active_after": capacity_after["active"],
                "launch_allowed": capacity_after["launch_allowed"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

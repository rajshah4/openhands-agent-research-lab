#!/usr/bin/env python3
"""Run one restartable Agent Canvas campaign tick from Kubernetes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from research_lab.cli import main as research_lab_main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument(
        "--base-url",
        default=os.environ.get(
            "CANVAS_BASE_URL",
            "http://agent-canvas-research:8000",
        ),
    )
    parser.add_argument(
        "--workspace-root",
        default="/home/openhands/workspace/neurogolf-controller",
    )
    parser.add_argument("--profile", default=os.environ.get("CANVAS_PROFILE"))
    parser.add_argument("--execution-timeout", type=int, default=1200)
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected an object in {path}")
    return value


def matching_runs(store: Path, campaign_id: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for manifest_path in sorted((store / "runs").glob("*/manifest.json")):
        manifest = load_object(manifest_path)
        campaign = manifest.get("campaign") or {}
        if campaign.get("id") != campaign_id:
            continue
        run_id = str(manifest["id"])
        attempts = len(list((manifest_path.parent / "attempts").glob("*.json")))
        matches.append(
            {
                "run_id": run_id,
                "attempts": attempts,
                "attempt_budget": int(campaign["attempt_budget"]),
            }
        )
    return matches


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> int:
    args = parse_args()
    campaign = load_object(args.campaign)
    campaign_id = str(campaign["id"])
    matches = matching_runs(args.store, campaign_id)
    incomplete = [
        item for item in matches if item["attempts"] < item["attempt_budget"]
    ]

    if len(incomplete) > 1:
        raise RuntimeError(
            f"multiple incomplete runs exist for campaign {campaign_id}"
        )
    if not incomplete and matches:
        latest = matches[-1]
        status = {
            "campaign_id": campaign_id,
            "state": "complete",
            **latest,
        }
        atomic_json(args.store / "controller-status.json", status)
        print(json.dumps(status, indent=2, sort_keys=True))
        return 0

    resume_run = incomplete[0]["run_id"] if incomplete else None
    planned = {
        "campaign_id": campaign_id,
        "state": "resume" if resume_run else "start",
        "resume_run_id": resume_run,
        "store": str(args.store),
        "base_url": args.base_url,
        "max_new_attempts": 1,
    }
    if args.dry_run:
        print(json.dumps(planned, indent=2, sort_keys=True))
        return 0

    command = [
        "run",
        "--campaign",
        str(args.campaign),
        "--store",
        str(args.store),
        "--worker",
        "canvas",
        "--base-url",
        args.base_url,
        "--canvas-remote-workspace",
        "--canvas-workspace-root",
        args.workspace_root,
        "--canvas-launch-lock-at",
        "2",
        "--max-new-attempts",
        "1",
        "--execution-timeout",
        str(args.execution_timeout),
        "--poll-seconds",
        str(args.poll_seconds),
        "--live",
    ]
    if args.profile:
        command.extend(["--canvas-profile", args.profile])
    if resume_run:
        command.extend(["--resume-run", resume_run])

    exit_code = research_lab_main(command)
    after = matching_runs(args.store, campaign_id)
    active = [
        item for item in after if item["attempts"] < item["attempt_budget"]
    ]
    latest = active[0] if active else (after[-1] if after else {})
    status = {
        "campaign_id": campaign_id,
        "state": (
            "failed"
            if exit_code
            else (
                "complete"
                if latest
                and latest.get("attempts", 0)
                >= latest.get("attempt_budget", 1)
                else "waiting-for-next-tick"
            )
        ),
        "exit_code": exit_code,
        **latest,
    }
    atomic_json(args.store / "controller-status.json", status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

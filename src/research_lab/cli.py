from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

from .canvas import CanvasClient, CanvasWorker
from .domain import CampaignSpec
from .comparison import MatchedComparisonRunner
from .openhands import (
    OpenHandsAPIError,
    OpenHandsClient,
    configured_api_key,
    configured_base_url,
)
from .runner import CampaignRunner
from .scheduler import policy_for
from .store import FileResearchStore
from .workers import LocalHeuristicWorker, OpenHandsWorker


def _load_env_file(path: Path | None) -> None:
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


def _campaign(args: argparse.Namespace) -> CampaignSpec:
    campaign = CampaignSpec.from_path(args.campaign.resolve())
    requested_task_ids = tuple(getattr(args, "task_ids", ()) or ())
    if requested_task_ids:
        requested = set(requested_task_ids)
        available = {task.id for task in campaign.tasks}
        unknown = sorted(requested - available)
        if unknown:
            raise ValueError(
                "unknown campaign task IDs: " + ", ".join(unknown)
            )
        campaign = replace(
            campaign,
            tasks=tuple(
                task for task in campaign.tasks if task.id in requested
            ),
        )
    if getattr(args, "policy", None):
        campaign = replace(campaign, policy=args.policy)
    if getattr(args, "attempts", None):
        campaign = replace(campaign, attempt_budget=args.attempts)
    if getattr(args, "repository", None):
        campaign = replace(campaign, repository=args.repository)
    if getattr(args, "branch", None):
        campaign = replace(campaign, branch=args.branch)
    return campaign


def _client(args: argparse.Namespace) -> OpenHandsClient:
    _load_env_file(args.env_file)
    return OpenHandsClient(
        configured_base_url(args.base_url),
        configured_api_key(),
    )


def _canvas_client(args: argparse.Namespace) -> CanvasClient:
    _load_env_file(args.env_file)
    api_key = (
        os.getenv("CANVAS_API_KEY")
        or os.getenv("LOCAL_BACKEND_API_KEY")
        or os.getenv("OH_SESSION_API_KEY")
    )
    if not api_key:
        raise OpenHandsAPIError(
            "missing Canvas session key; set CANVAS_API_KEY, "
            "LOCAL_BACKEND_API_KEY, or OH_SESSION_API_KEY"
        )
    return CanvasClient(
        (args.base_url or "http://127.0.0.1:8000").rstrip("/"),
        api_key.strip(),
    )


def command_preflight(args: argparse.Namespace) -> int:
    campaign = _campaign(args)
    checks = {
        "campaign": campaign.id,
        "tasks": len(campaign.tasks),
        "attempt_budget": campaign.attempt_budget,
        "repository": campaign.repository,
        "branch": campaign.branch,
        "worker": args.worker,
    }
    if args.worker == "openhands":
        client = _client(args)
        identity = client.preflight()
        checks.update(
            {
                "base_url": client.base_url,
                "authentication": "passed",
                "identity_fields": sorted(identity.keys()),
                "capacity": client.capacity_snapshot(
                    runtime_limit=args.runtime_capacity,
                    launch_lock_at=args.launch_lock_at,
                ),
            }
        )
    elif args.worker == "canvas":
        client = _canvas_client(args)
        checks.update(
            {
                "base_url": client.base_url,
                "authentication": "passed",
                "canvas": client.preflight(),
                "capacity": client.capacity_snapshot(
                    launch_lock_at=args.canvas_launch_lock_at,
                ),
                "execution_boundary": (
                    "shared-remote-workspace"
                    if args.canvas_remote_workspace
                    else "shared-local-workspace"
                ),
            }
        )
    else:
        checks["authentication"] = "not-required"
    print(json.dumps(checks, indent=2, sort_keys=True))
    return 0


def command_run(args: argparse.Namespace) -> int:
    campaign = _campaign(args)
    if args.worker == "openhands":
        if not args.live:
            raise ValueError(
                "OpenHands execution creates real conversations; pass --live after preflight"
            )
        worker = OpenHandsWorker(
            _client(args),
            start_timeout_seconds=args.start_timeout,
            execution_timeout_seconds=args.execution_timeout,
            poll_seconds=args.poll_seconds,
            pause_after_attempt=not args.keep_sandbox,
            runtime_limit=args.runtime_capacity,
            launch_lock_at=args.launch_lock_at,
        )
    elif args.worker == "canvas":
        if not args.live:
            raise ValueError(
                "Canvas execution makes real model calls; pass --live after preflight"
            )
        workspace_root = args.canvas_workspace_root
        if not args.canvas_remote_workspace:
            workspace_root = workspace_root.resolve()
        worker = CanvasWorker(
            _canvas_client(args),
            workspace_root=workspace_root,
            max_iterations=args.max_iterations,
            execution_timeout_seconds=args.execution_timeout,
            poll_seconds=args.poll_seconds,
            launch_lock_at=args.canvas_launch_lock_at,
            profile=args.canvas_profile,
            prepare_workspace_locally=not args.canvas_remote_workspace,
        )
    else:
        worker = LocalHeuristicWorker()

    store = FileResearchStore(args.store.resolve())
    runner = CampaignRunner(
        store=store,
        worker=worker,
        scheduler=policy_for(campaign.policy),
    )
    run_id, report = runner.run(
        campaign,
        resume_run_id=args.resume_run,
        max_new_attempts=args.max_new_attempts,
    )
    print(report)
    print(f"Artifacts: {args.store.resolve() / 'runs' / run_id}")
    return 0


def _worker(
    args: argparse.Namespace,
) -> LocalHeuristicWorker | OpenHandsWorker | CanvasWorker:
    if args.worker == "openhands":
        if not args.live:
            raise ValueError(
                "OpenHands execution creates real conversations; pass --live after preflight"
            )
        return OpenHandsWorker(
            _client(args),
            start_timeout_seconds=args.start_timeout,
            execution_timeout_seconds=args.execution_timeout,
            poll_seconds=args.poll_seconds,
            pause_after_attempt=not args.keep_sandbox,
            runtime_limit=args.runtime_capacity,
            launch_lock_at=args.launch_lock_at,
        )
    if args.worker == "canvas":
        if not args.live:
            raise ValueError(
                "Canvas execution makes real model calls; pass --live after preflight"
            )
        workspace_root = args.canvas_workspace_root
        if not args.canvas_remote_workspace:
            workspace_root = workspace_root.resolve()
        return CanvasWorker(
            _canvas_client(args),
            workspace_root=workspace_root,
            max_iterations=args.max_iterations,
            execution_timeout_seconds=args.execution_timeout,
            poll_seconds=args.poll_seconds,
            launch_lock_at=args.canvas_launch_lock_at,
            profile=args.canvas_profile,
            prepare_workspace_locally=not args.canvas_remote_workspace,
        )
    return LocalHeuristicWorker()


def command_compare(args: argparse.Namespace) -> int:
    campaign = _campaign(args)
    comparison_id, _, report = MatchedComparisonRunner(
        root=args.store.resolve(),
        worker=_worker(args),
    ).run(campaign)
    print(report)
    print(f"Artifacts: {args.store.resolve() / 'comparisons' / comparison_id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run bounded, validated research campaigns with OpenHands workers."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--campaign", required=True, type=Path)
        subparser.add_argument(
            "--task-id",
            dest="task_ids",
            action="append",
            help=(
                "restrict execution to an exact campaign task; repeat to select "
                "multiple tasks"
            ),
        )
        subparser.add_argument(
            "--worker",
            choices=("local", "openhands", "canvas"),
            default="local",
        )
        subparser.add_argument("--policy", choices=("managed", "round_robin", "naive"))
        subparser.add_argument("--attempts", type=int)
        subparser.add_argument("--repository")
        subparser.add_argument("--branch")
        subparser.add_argument("--base-url")
        subparser.add_argument("--env-file", type=Path)
        subparser.add_argument(
            "--canvas-workspace-root",
            type=Path,
            default=Path(".lab-canvas-workspaces"),
            help="dedicated root for per-attempt Canvas workspaces",
        )
        subparser.add_argument(
            "--canvas-remote-workspace",
            action="store_true",
            help=(
                "treat --canvas-workspace-root as an absolute path on a remote "
                "Canvas backend; do not create it on the controller"
            ),
        )
        subparser.add_argument(
            "--canvas-launch-lock-at",
            type=int,
            default=2,
            help="refuse a Canvas launch at or above this running-conversation count",
        )
        subparser.add_argument(
            "--canvas-profile",
            help="require this Canvas profile to already be active; never switches it",
        )
        subparser.add_argument(
            "--runtime-capacity",
            type=int,
            default=10,
            help="documented runtime ceiling for the target OpenHands instance",
        )
        subparser.add_argument(
            "--launch-lock-at",
            type=int,
            default=7,
            help="refuse new conversations at or above this active-sandbox count",
        )

    preflight = subparsers.add_parser(
        "preflight",
        help="validate a campaign and optionally test OpenHands authentication",
    )
    common(preflight)
    preflight.set_defaults(func=command_preflight)

    run = subparsers.add_parser("run", help="execute a campaign")
    common(run)
    run.add_argument("--store", type=Path, default=Path(".lab"))
    run.add_argument(
        "--resume-run",
        help=(
            "resume and reconcile this existing run ID instead of creating "
            "a new run"
        ),
    )
    run.add_argument(
        "--max-new-attempts",
        type=int,
        help=(
            "finish at most this many new or recovered attempts before exiting; "
            "useful for scheduled controller ticks"
        ),
    )
    run.add_argument("--live", action="store_true")
    run.add_argument("--start-timeout", type=int, default=600)
    run.add_argument("--execution-timeout", type=int, default=1800)
    run.add_argument("--poll-seconds", type=int, default=10)
    run.add_argument("--max-iterations", type=int, default=50)
    run.add_argument(
        "--keep-sandbox",
        action="store_true",
        help="leave live sandboxes running for debugging instead of pausing them",
    )
    run.set_defaults(func=command_run)

    compare = subparsers.add_parser(
        "compare",
        help="run isolated naive and managed arms with a matched fixed budget",
    )
    common(compare)
    compare.add_argument("--store", type=Path, default=Path(".lab-comparison"))
    compare.add_argument("--live", action="store_true")
    compare.add_argument("--start-timeout", type=int, default=600)
    compare.add_argument("--execution-timeout", type=int, default=1800)
    compare.add_argument("--poll-seconds", type=int, default=10)
    compare.add_argument("--max-iterations", type=int, default=50)
    compare.add_argument(
        "--keep-sandbox",
        action="store_true",
        help="leave live sandboxes running for debugging instead of pausing them",
    )
    compare.set_defaults(func=command_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (OpenHandsAPIError, TimeoutError, RuntimeError, ValueError, OSError) as exc:
        print(f"research-lab: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

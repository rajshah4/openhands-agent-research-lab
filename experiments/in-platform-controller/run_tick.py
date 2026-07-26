"""Run one checkpointed controller tick from a Replicated sandbox."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from research_lab.domain import CampaignSpec
from research_lab.openhands import OpenHandsClient, configured_api_key, configured_base_url
from research_lab.runner import CampaignRunner
from research_lab.scheduler import policy_for
from research_lab.store import FileResearchStore
from research_lab.workers import LocalHeuristicWorker, OpenHandsWorker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAMPAIGN = PROJECT_ROOT / "examples" / "in-platform-controller-pilot.json"
DEFAULT_STATE_ROOT = PROJECT_ROOT / ".campaign-state" / "in-platform-controller"


def _run_git(arguments: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=True,
        stdin=subprocess.DEVNULL,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class GitCheckpoint:
    """Commit and push every durable controller transition."""

    def __init__(self, repository: Path, state_root: Path, branch: str):
        self.repository = repository.resolve()
        self.state_root = state_root.resolve()
        self.branch = branch
        self.relative_state = self.state_root.relative_to(self.repository)

    def __call__(self, reason: str) -> None:
        _run_git(["add", "--", str(self.relative_state)], cwd=self.repository)
        status = _run_git(
            ["status", "--short", "--", str(self.relative_state)],
            cwd=self.repository,
        )
        if not status.stdout.strip():
            return
        safe_reason = "".join(
            character if character.isalnum() or character in "-_ " else "-"
            for character in reason
        )[:80]
        _run_git(
            ["commit", "-m", f"checkpoint: {safe_reason}"],
            cwd=self.repository,
        )
        _run_git(
            ["push", "origin", f"HEAD:refs/heads/{self.branch}"],
            cwd=self.repository,
        )


class CheckpointingFileResearchStore:
    """File store that pushes state before the controller advances."""

    def __init__(self, root: Path, checkpoint: Callable[[str], None]):
        self.inner = FileResearchStore(root)
        self.root = self.inner.root
        self.checkpoint = checkpoint

    @contextmanager
    def controller_lock(self) -> Iterator[None]:
        with self.inner.controller_lock():
            yield

    def create_run(self, run_id: str, manifest: dict[str, Any]) -> None:
        self.inner.create_run(run_id, manifest)
        self.checkpoint(f"create run {run_id}")

    def read_run_manifest(self, run_id: str) -> dict[str, Any]:
        return self.inner.read_run_manifest(run_id)

    def append_lifecycle_event(
        self,
        run_id: str,
        attempt_id: str,
        event: dict[str, Any],
    ) -> None:
        before = len(self.inner.list_lifecycle_events(run_id, attempt_id))
        self.inner.append_lifecycle_event(run_id, attempt_id, event)
        after = len(self.inner.list_lifecycle_events(run_id, attempt_id))
        if after > before:
            self.checkpoint(f"{attempt_id} {event.get('kind', 'lifecycle')}")

    def append_attempt(self, run_id: str, attempt: dict[str, Any]) -> None:
        self.inner.append_attempt(run_id, attempt)
        self.checkpoint(f"record {attempt.get('id', 'attempt')}")

    def list_attempts(self, run_id: str) -> list[dict[str, Any]]:
        return self.inner.list_attempts(run_id)

    def list_lifecycle_events(
        self,
        run_id: str,
        attempt_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.inner.list_lifecycle_events(run_id, attempt_id)

    def save_validated_lesson(self, lesson) -> None:
        path = self.root / "lessons" / "validated" / f"{lesson.id}.json"
        existed = path.exists()
        self.inner.save_validated_lesson(lesson)
        if not existed:
            self.checkpoint(f"promote {lesson.id}")

    def find_lessons(self, tags: tuple[str, ...], limit: int = 3):
        return self.inner.find_lessons(tags, limit)

    def write_report(self, run_id: str, report: str) -> Path:
        path = self.inner.write_report(run_id, report)
        self.checkpoint(f"report {run_id}")
        return path


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _discover_run_id(state_root: Path) -> str | None:
    manifests = sorted((state_root / "runs").glob("*/manifest.json"))
    if len(manifests) > 1:
        raise RuntimeError("state branch contains more than one controller run")
    return manifests[0].parent.name if manifests else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN)
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT)
    parser.add_argument("--state-branch", default=os.getenv("RESEARCH_STATE_BRANCH", ""))
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--start-timeout", type=int, default=600)
    parser.add_argument("--execution-timeout", type=int, default=1200)
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--runtime-capacity", type=int, default=10)
    parser.add_argument("--launch-lock-at", type=int, default=7)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository = PROJECT_ROOT.resolve()
    state_root = args.state_root.resolve()
    campaign = CampaignSpec.from_path(args.campaign.resolve())
    checkpoint: Callable[[str], None]
    if args.state_branch:
        checkpoint = GitCheckpoint(repository, state_root, args.state_branch)
    else:
        checkpoint = lambda reason: None
    store = CheckpointingFileResearchStore(state_root, checkpoint)

    run_id = _discover_run_id(state_root)
    if run_id and len(store.list_attempts(run_id)) >= campaign.attempt_budget:
        status = {
            "schema_version": 1,
            "campaign_id": campaign.id,
            "run_id": run_id,
            "status": "completed",
            "attempts_completed": campaign.attempt_budget,
        }
        _atomic_json(state_root / "controller.json", status)
        checkpoint("controller completed")
        print(json.dumps(status, sort_keys=True))
        return 0

    if args.live:
        worker = OpenHandsWorker(
            OpenHandsClient(configured_base_url(None), configured_api_key()),
            start_timeout_seconds=args.start_timeout,
            execution_timeout_seconds=args.execution_timeout,
            poll_seconds=args.poll_seconds,
            pause_after_attempt=True,
            runtime_limit=args.runtime_capacity,
            launch_lock_at=args.launch_lock_at,
        )
    else:
        worker = LocalHeuristicWorker()

    runner = CampaignRunner(
        store=store,
        worker=worker,
        scheduler=policy_for(campaign.policy),
    )
    run_id, _ = runner.run(
        campaign,
        resume_run_id=run_id,
        max_new_attempts=1,
    )
    attempts_completed = len(store.list_attempts(run_id))
    status = {
        "schema_version": 1,
        "campaign_id": campaign.id,
        "run_id": run_id,
        "status": (
            "completed"
            if attempts_completed >= campaign.attempt_budget
            else "running"
        ),
        "attempts_completed": attempts_completed,
    }
    _atomic_json(state_root / "controller.json", status)
    checkpoint(f"controller {status['status']}")
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

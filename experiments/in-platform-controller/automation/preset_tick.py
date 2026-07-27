"""Prepare the Git state branch and run one controller tick.

This entrypoint is invoked from a supported repository-backed prompt
automation. OpenHands owns repository authentication, stored-secret injection,
the run callback, and sandbox cleanup. This script owns only deterministic
controller preparation and execution.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STATE_BRANCH = "experiment/in-platform-controller-state"
DEFAULT_CAMPAIGN = "examples/in-platform-controller-pilot.json"
DEFAULT_STATE_ROOT = ".campaign-state/in-platform-controller"
TICK_SCRIPT = PROJECT_ROOT / "experiments" / "in-platform-controller" / "run_tick.py"


def _git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        check=check,
        stdin=subprocess.DEVNULL,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _prepare_state_branch(state_branch: str = DEFAULT_STATE_BRANCH) -> None:
    _git("config", "user.name", "OpenHands Research Controller")
    _git(
        "config",
        "user.email",
        "research-controller@users.noreply.github.com",
    )
    # Enterprise repository preparation may use a shallow clone. A state branch
    # created by an earlier run can then share history that is outside the
    # shallow boundary, causing a valid merge to fail with exit 128.
    _git("fetch", "--unshallow", "origin", check=False)
    remote_state = _git(
        "ls-remote",
        "--exit-code",
        "--heads",
        "origin",
        state_branch,
        check=False,
    )
    if remote_state.returncode == 0:
        _git(
            "fetch",
            "origin",
            f"{state_branch}:refs/remotes/origin/{state_branch}",
        )
        _git("checkout", "-B", state_branch, f"origin/{state_branch}")
        _git("merge", "--no-edit", "origin/main")
    else:
        _git("checkout", "-B", state_branch)


def _project_path(value: str, *, label: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    if PROJECT_ROOT not in path.parents:
        raise ValueError(f"{label} must resolve inside the repository")
    return path


def main() -> int:
    if not os.environ.get("OPENHANDS_API_KEY"):
        raise RuntimeError(
            "OPENHANDS_API_KEY was not injected into the automation conversation"
        )
    state_branch = os.environ.get("RESEARCH_STATE_BRANCH", DEFAULT_STATE_BRANCH)
    if not state_branch.startswith("experiment/"):
        raise ValueError("RESEARCH_STATE_BRANCH must start with experiment/")
    campaign = _project_path(
        os.environ.get("RESEARCH_CAMPAIGN", DEFAULT_CAMPAIGN),
        label="RESEARCH_CAMPAIGN",
    )
    state_root = _project_path(
        os.environ.get("RESEARCH_STATE_ROOT", DEFAULT_STATE_ROOT),
        label="RESEARCH_STATE_ROOT",
    )
    _prepare_state_branch(state_branch)
    environment = dict(os.environ)
    environment.update(
        {
            "OPENHANDS_BASE_URL": environment.get(
                "OPENHANDS_BASE_URL",
                "https://app.replicated.rajistics.com",
            ),
            "RESEARCH_STATE_BRANCH": state_branch,
            "PYTHONPATH": str(PROJECT_ROOT / "src"),
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(TICK_SCRIPT),
            "--campaign",
            str(campaign),
            "--state-root",
            str(state_root),
            "--live",
            "--defer-sandbox-cleanup",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

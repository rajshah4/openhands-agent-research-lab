"""Bootstrap one deterministic in-platform controller tick."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


REPOSITORY = "https://github.com/rajshah4/openhands-agent-research-lab.git"
DEFAULT_BRANCH = "main"
STATE_BRANCH = "experiment/in-platform-controller-state"
TICK_SCRIPT = "experiments/in-platform-controller/run_tick.py"


def get_secret(name):
    """Fetch a named secret stored in the agent server."""
    url = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
    key = os.environ.get("SESSION_API_KEY") or os.environ.get("OH_SESSION_API_KEYS_0", "")
    with urllib.request.urlopen(urllib.request.Request(
        f"{url}/api/settings/secrets/{name}", headers={"X-Session-API-Key": key}
    )) as r:
        return r.read().decode().strip()


def fire_callback(status="COMPLETED", error=None):
    """Signal run completion. MUST be called on every exit path — success AND error."""
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url: return
    body = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error: body["error"] = error
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('AUTOMATION_CALLBACK_API_KEY', '')}",
        }))
    except Exception as e: print(f"Callback error: {e}")


def _git_environment(token: str) -> dict[str, str]:
    encoded = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {encoded}",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _run(
    arguments: list[str],
    *,
    cwd: Path | None = None,
    environment: dict[str, str] | None = None,
) -> None:
    subprocess.run(
        arguments,
        cwd=cwd,
        env=environment,
        check=True,
        stdin=subprocess.DEVNULL,
    )


def _clone_state_branch(destination: Path, git_environment: dict[str, str]) -> None:
    branch_check = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", REPOSITORY, STATE_BRANCH],
        env=git_environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if branch_check.returncode == 0:
        _run(
            [
                "git",
                "clone",
                "--quiet",
                "--single-branch",
                "--branch",
                STATE_BRANCH,
                REPOSITORY,
                str(destination),
            ],
            environment=git_environment,
        )
        return

    _run(
        [
            "git",
            "clone",
            "--quiet",
            "--single-branch",
            "--branch",
            DEFAULT_BRANCH,
            REPOSITORY,
            str(destination),
        ],
        environment=git_environment,
    )
    _run(["git", "checkout", "-b", STATE_BRANCH], cwd=destination)


def main() -> int:
    github_token = get_secret("GITHUB_TOKEN")
    openhands_api_key = get_secret("OPENHANDS_API_KEY")
    if not github_token or not openhands_api_key:
        raise RuntimeError("required stored credentials are unavailable")

    git_environment = _git_environment(github_token)
    with tempfile.TemporaryDirectory(prefix="research-controller-") as directory:
        repository = Path(directory) / "repository"
        _clone_state_branch(repository, git_environment)
        _run(["git", "config", "user.name", "OpenHands Research Controller"], cwd=repository)
        _run(
            ["git", "config", "user.email", "research-controller@users.noreply.github.com"],
            cwd=repository,
        )

        environment = dict(git_environment)
        environment.update(
            {
                "OPENHANDS_BASE_URL": "https://app.replicated.rajistics.com",
                "OPENHANDS_API_KEY": openhands_api_key,
                "RESEARCH_STATE_BRANCH": STATE_BRANCH,
                "PYTHONPATH": str(repository / "src"),
            }
        )
        _run(
            [sys.executable, TICK_SCRIPT, "--live"],
            cwd=repository,
            environment=environment,
        )

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as exc:
        print(f"controller tick failed: {type(exc).__name__}", file=sys.stderr)
        fire_callback("FAILED", str(exc))
        raise SystemExit(1)
    fire_callback("COMPLETED")
    raise SystemExit(exit_code)

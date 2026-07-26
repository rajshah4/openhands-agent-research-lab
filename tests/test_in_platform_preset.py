from __future__ import annotations

import importlib.util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "in-platform-controller"
    / "automation"
    / "preset_tick.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("preset_tick", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_state_branch_resumes_remote_branch(monkeypatch):
    module = _load_module()
    calls: list[tuple[tuple[str, ...], bool]] = []

    class Result:
        returncode = 0

    def fake_git(*arguments: str, check: bool = True):
        calls.append((arguments, check))
        return Result()

    monkeypatch.setattr(module, "_git", fake_git)
    module._prepare_state_branch()

    assert (
        (
            "fetch",
            "origin",
            "experiment/in-platform-controller-state:"
            "refs/remotes/origin/experiment/in-platform-controller-state",
        ),
        True,
    ) in calls
    assert (
        (
            "checkout",
            "-B",
            "experiment/in-platform-controller-state",
            "origin/experiment/in-platform-controller-state",
        ),
        True,
    ) in calls


def test_prepare_state_branch_creates_branch_when_remote_is_absent(monkeypatch):
    module = _load_module()
    calls: list[tuple[tuple[str, ...], bool]] = []

    class Result:
        returncode = 2

    def fake_git(*arguments: str, check: bool = True):
        calls.append((arguments, check))
        return Result()

    monkeypatch.setattr(module, "_git", fake_git)
    module._prepare_state_branch()

    assert (
        ("checkout", "-B", "experiment/in-platform-controller-state"),
        True,
    ) in calls

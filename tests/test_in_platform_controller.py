import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "in-platform-controller"
    / "run_tick.py"
)
SPEC = importlib.util.spec_from_file_location("in_platform_controller", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
GitCheckpoint = MODULE.GitCheckpoint


def test_defer_sandbox_cleanup_flag() -> None:
    args = MODULE.build_parser().parse_args(["--defer-sandbox-cleanup"])
    assert args.defer_sandbox_cleanup is True


def git(cwd: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class GitCheckpointTests(unittest.TestCase):
    def test_remote_branch_rejects_second_controller_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            seed = root / "seed"
            first = root / "first"
            second = root / "second"
            git(root, "init", "--bare", str(remote))
            git(root, "clone", str(remote), str(seed))
            git(seed, "config", "user.name", "Test Controller")
            git(seed, "config", "user.email", "controller@example.test")
            (seed / "README.md").write_text("seed\n", encoding="utf-8")
            git(seed, "add", "README.md")
            git(seed, "commit", "-m", "seed")
            git(seed, "branch", "-M", "main")
            git(seed, "push", "-u", "origin", "main")
            git(root, "clone", "--branch", "main", str(remote), str(first))
            git(root, "clone", "--branch", "main", str(remote), str(second))

            for repository, value in ((first, "first"), (second, "second")):
                git(repository, "config", "user.name", "Test Controller")
                git(repository, "config", "user.email", "controller@example.test")
                state = repository / ".campaign-state" / "in-platform-controller"
                state.mkdir(parents=True)
                (state / "claim.txt").write_text(value + "\n", encoding="utf-8")

            GitCheckpoint(
                first,
                first / ".campaign-state" / "in-platform-controller",
                "experiment/state",
            )("first claim")

            with self.assertRaises(subprocess.CalledProcessError):
                GitCheckpoint(
                    second,
                    second / ".campaign-state" / "in-platform-controller",
                    "experiment/state",
                )("second claim")


if __name__ == "__main__":
    unittest.main()

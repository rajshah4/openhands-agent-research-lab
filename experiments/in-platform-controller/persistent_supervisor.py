"""Run bounded controller ticks inside one persistent Replicated sandbox."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


TICK_SCRIPT = Path(__file__).with_name("run_tick.py")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticks", type=int, default=4)
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    if args.ticks < 1:
        raise ValueError("ticks must be at least 1")
    if args.interval_seconds < 0:
        raise ValueError("interval_seconds cannot be negative")

    for index in range(args.ticks):
        command = [sys.executable, str(TICK_SCRIPT)]
        if args.live:
            command.append("--live")
        subprocess.run(command, check=True)
        if index + 1 < args.ticks:
            time.sleep(args.interval_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

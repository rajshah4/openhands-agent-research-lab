#!/usr/bin/env python3
"""Run a deliberately slow local campaign for controller crash testing."""

from __future__ import annotations

import argparse
import time
from dataclasses import replace
from pathlib import Path

from research_lab.domain import CampaignSpec
from research_lab.runner import CampaignRunner
from research_lab.scheduler import policy_for
from research_lab.store import FileResearchStore
from research_lab.workers import LocalHeuristicWorker


class SlowLocalWorker(LocalHeuristicWorker):
    def __init__(self, delay_seconds: float):
        self.delay_seconds = delay_seconds

    def execute(self, **kwargs):  # type: ignore[no-untyped-def]
        time.sleep(self.delay_seconds)
        return super().execute(**kwargs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--attempts", type=int, required=True)
    parser.add_argument("--delay-seconds", type=float, default=0.25)
    args = parser.parse_args()

    campaign = replace(
        CampaignSpec.from_path(args.campaign.resolve()),
        attempt_budget=args.attempts,
    )
    runner = CampaignRunner(
        store=FileResearchStore(args.store.resolve()),
        worker=SlowLocalWorker(args.delay_seconds),
        scheduler=policy_for(campaign.policy),
    )
    run_id, _ = runner.run(campaign)
    print(run_id)


if __name__ == "__main__":
    main()

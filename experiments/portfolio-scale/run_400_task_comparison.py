#!/usr/bin/env python3
"""Run a 400-task, 4,800-attempt matched orchestration simulation."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from research_lab.comparison import MatchedComparisonRunner
from research_lab.domain import CampaignSpec, TaskSpec
from research_lab.workers import LocalHeuristicWorker


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _template(path: str) -> TaskSpec:
    return TaskSpec.from_path(PROJECT_ROOT / path)


def campaign() -> CampaignSpec:
    templates = (
        _template("examples/tasks/scale/color-wheel-8.json"),
        _template("examples/tasks/scale/cover-campus.json"),
        _template("examples/tasks/scale/pack-alpha.json"),
    )
    tasks = tuple(
        replace(
            templates[index % len(templates)],
            id=f"task{index + 1:03d}",
            tags=(
                *templates[index % len(templates)].tags,
                f"portfolio-{index + 1:03d}",
            ),
        )
        for index in range(400)
    )
    return CampaignSpec(
        id="neurogolf-400-task-orchestration-simulation",
        name="NeuroGolf-sized orchestration simulation",
        policy="managed",
        attempt_budget=4800,
        repository="rajshah4/openhands-agent-research-lab",
        branch="main",
        model=None,
        tasks=tasks,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True, type=Path)
    args = parser.parse_args()
    comparison_id, comparison, _ = MatchedComparisonRunner(
        root=args.store.resolve(),
        worker=LocalHeuristicWorker(),
    ).run(campaign())
    metric_keys = (
        "problems_solved",
        "coverage",
        "normalized_solution_quality",
        "quality_auc",
        "duplicate_experiments",
        "retrieved_lessons",
        "improvements",
    )
    print(
        json.dumps(
            {
                "comparison_id": comparison_id,
                "attempt_budget_per_arm": comparison["attempt_budget"],
                "task_count": comparison["task_count"],
                "arms": {
                    name: {
                        key: value["metrics"][key]
                        for key in metric_keys
                    }
                    for name, value in comparison["arms"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

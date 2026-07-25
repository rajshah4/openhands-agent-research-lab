from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .domain import CampaignSpec, utc_now
from .runner import CampaignRunner, _best_score, _normalized_quality
from .scheduler import policy_for
from .store import FileResearchStore
from .workers import WorkerBackend


def _comparison_id(campaign_id: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{campaign_id}-comparison-{timestamp}-{uuid.uuid4().hex[:8]}"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        temporary_path = Path(temporary_name)
        if temporary_path.exists():
            temporary_path.unlink()


def summarize_arm(
    campaign: CampaignSpec,
    attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    task_ids = {task.id for task in campaign.tasks}
    attempted = {str(attempt["task_id"]) for attempt in attempts}
    solved = {
        str(attempt["task_id"])
        for attempt in attempts
        if attempt.get("validation", {}).get("valid")
    }
    best_scores = {
        task.id: _best_score(attempts, task.id)
        for task in campaign.tasks
    }
    quality_trajectory = [
        _normalized_quality(campaign, attempts[:sequence])
        for sequence in range(1, len(attempts) + 1)
    ]
    return {
        "attempts": len(attempts),
        "problems_solved": len(solved),
        "task_count": len(task_ids),
        "coverage": len(attempted) / len(task_ids),
        "best_scores": best_scores,
        "aggregate_best_score": (
            sum(float(score) for score in best_scores.values() if score is not None)
            if all(score is not None for score in best_scores.values())
            else None
        ),
        "normalized_solution_quality": _normalized_quality(campaign, attempts),
        "quality_auc": (
            sum(quality_trajectory) / len(quality_trajectory)
            if quality_trajectory
            else 0.0
        ),
        "duplicate_experiments": sum(
            1 for attempt in attempts if attempt.get("duplicate_candidate")
        ),
        "improvements": sum(1 for attempt in attempts if attempt.get("improved")),
        "improvement_per_attempt": (
            sum(1 for attempt in attempts if attempt.get("improved")) / len(attempts)
            if attempts
            else 0.0
        ),
    }


def _report(comparison: dict[str, Any]) -> str:
    arms = comparison["arms"]
    lines = [
        f"# Matched comparison: {comparison['id']}",
        "",
        f"- Campaign: {comparison['campaign_id']}",
        f"- Worker: {comparison['worker_kind']}",
        f"- Fixed budget per arm: {comparison['attempt_budget']} attempts",
        f"- Tasks per arm: {comparison['task_count']}",
        "",
        "Both arms used the same tasks, worker backend, model configuration, and",
        "attempt budget. Their stores were isolated so evidence could not leak",
        "between arms.",
        "",
        "## Results",
        "",
        "| Metric | Naive | Managed |",
        "| --- | ---: | ---: |",
    ]
    metric_rows = (
        ("Problems solved", "problems_solved", ".0f"),
        ("Coverage", "coverage", ".3f"),
        ("Normalized solution quality", "normalized_solution_quality", ".3f"),
        ("Quality AUC", "quality_auc", ".3f"),
        ("Duplicate experiments", "duplicate_experiments", ".0f"),
        ("Improvement per attempt", "improvement_per_attempt", ".3f"),
    )
    for label, key, format_spec in metric_rows:
        naive = format(arms["naive"]["metrics"][key], format_spec)
        managed = format(arms["managed"]["metrics"][key], format_spec)
        lines.append(f"| {label} | {naive} | {managed} |")
    lines.extend(
        [
            "",
            "The offline worker is deterministic test instrumentation, not evidence",
            "about model performance. A live OpenHands comparison must keep the same",
            "contract and budget before making production claims.",
        ]
    )
    return "\n".join(lines) + "\n"


class MatchedComparisonRunner:
    def __init__(self, *, root: Path, worker: WorkerBackend):
        self.root = root
        self.worker = worker

    def run(self, campaign: CampaignSpec) -> tuple[str, dict[str, Any], str]:
        comparison_id = _comparison_id(campaign.id)
        comparison_path = self.root / "comparisons" / comparison_id
        arms: dict[str, Any] = {}

        for policy_name in ("naive", "managed"):
            arm_campaign = replace(
                campaign,
                id=f"{campaign.id}-{policy_name}",
                policy=policy_name,
            )
            arm_store = FileResearchStore(comparison_path / "arms" / policy_name)
            runner = CampaignRunner(
                store=arm_store,
                worker=self.worker,
                scheduler=policy_for(policy_name),
            )
            run_id, _ = runner.run(arm_campaign)
            attempts = arm_store.list_attempts(run_id)
            arms[policy_name] = {
                "run_id": run_id,
                "metrics": summarize_arm(arm_campaign, attempts),
            }

        comparison = {
            "schema_version": 1,
            "id": comparison_id,
            "created_at": utc_now(),
            "campaign_id": campaign.id,
            "worker_kind": type(self.worker).__name__,
            "attempt_budget": campaign.attempt_budget,
            "task_count": len(campaign.tasks),
            "matched_configuration": {
                "repository": campaign.repository,
                "branch": campaign.branch,
                "model": campaign.model,
                "task_ids": [task.id for task in campaign.tasks],
            },
            "arms": arms,
        }
        report = _report(comparison)
        _atomic_write(
            comparison_path / "comparison.json",
            json.dumps(comparison, indent=2, sort_keys=True) + "\n",
        )
        _atomic_write(comparison_path / "report.md", report)
        return comparison_id, comparison, report

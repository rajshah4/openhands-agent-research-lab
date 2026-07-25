from __future__ import annotations

import json
import os
import tempfile
import argparse
from pathlib import Path
from typing import Any

from .domain import utc_now
from .openhands import sanitize_metadata
from .store import FileResearchStore


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        temporary = Path(temporary_name)
        if temporary.exists():
            temporary.unlink()


def _paused(
    comparison_root: Path,
    arm: str,
    run_id: str,
    attempt_id: str,
) -> bool:
    lifecycle = (
        comparison_root
        / "arms"
        / arm
        / "runs"
        / run_id
        / "lifecycle"
        / attempt_id
    )
    return any(lifecycle.glob("*-sandbox_paused.json"))


def export_comparison_evidence(
    comparison_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Export a public-safe structured view of a matched comparison ledger."""
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    comparison_root = comparison_path.parent
    exported_arms: dict[str, Any] = {}

    for arm, arm_record in comparison["arms"].items():
        run_id = str(arm_record["run_id"])
        arm_root = comparison_root / "arms" / arm
        attempts = FileResearchStore(arm_root).list_attempts(run_id)
        exported_attempts = []
        for attempt in attempts:
            conversation = sanitize_metadata(attempt.get("conversation", {}))
            exported_attempts.append(
                {
                    "id": attempt["id"],
                    "sequence": attempt["sequence"],
                    "task_id": attempt["task_id"],
                    "scheduler_decision": attempt.get("scheduler_decision", {}),
                    "retrieved_lesson_ids": attempt.get("retrieved_lesson_ids", []),
                    "worker_kind": attempt.get("worker_kind"),
                    "conversation": conversation,
                    "sandbox_paused": _paused(
                        comparison_root,
                        arm,
                        run_id,
                        str(attempt["id"]),
                    ),
                    "outcome": attempt.get("outcome"),
                    "contract": attempt.get("contract"),
                    "candidate_hash": attempt.get("candidate_hash"),
                    "duplicate_candidate": attempt.get("duplicate_candidate", False),
                    "validation": attempt.get("validation"),
                    "improved": attempt.get("improved", False),
                    "promoted_lesson_id": attempt.get("promoted_lesson_id"),
                }
            )

        lessons = []
        for path in sorted((arm_root / "lessons" / "validated").glob("*.json")):
            lessons.append(json.loads(path.read_text(encoding="utf-8")))
        exported_arms[arm] = {
            "run_id": run_id,
            "metrics": arm_record["metrics"],
            "attempts": exported_attempts,
            "validated_lessons": lessons,
        }

    evidence = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "comparison": {
            "id": comparison["id"],
            "created_at": comparison["created_at"],
            "campaign_id": comparison["campaign_id"],
            "worker_kind": comparison["worker_kind"],
            "attempt_budget": comparison["attempt_budget"],
            "task_count": comparison["task_count"],
            "matched_configuration": comparison["matched_configuration"],
        },
        "arms": exported_arms,
    }
    _atomic_json(output_path, evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a sanitized structured evidence bundle."
    )
    parser.add_argument("--comparison", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    evidence = export_comparison_evidence(
        args.comparison.resolve(),
        args.output.resolve(),
    )
    print(
        json.dumps(
            {
                "comparison": evidence["comparison"]["id"],
                "attempts": sum(
                    len(arm["attempts"]) for arm in evidence["arms"].values()
                ),
                "output": str(args.output.resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

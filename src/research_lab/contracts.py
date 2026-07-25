from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


ALLOWED_STATUSES = {"done", "needs-human", "failed"}
ALLOWED_GATES = {"validate", "human-review", "stop"}
REQUIRED_FIELDS = {"status", "candidate", "lesson", "summary", "next_gate"}


class ContractError(ValueError):
    """Raised when a worker final response violates the output contract."""


@dataclass(frozen=True)
class LessonProposal:
    statement: str
    tags: tuple[str, ...]
    evidence: str


@dataclass(frozen=True)
class WorkerContract:
    status: str
    candidate: dict[str, Any] | None
    lesson: LessonProposal | None
    summary: tuple[str, ...]
    next_gate: str
    transport: str


def _json_object_from_text(text: str) -> tuple[dict[str, Any], str]:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        decoder = json.JSONDecoder()
        candidates: list[dict[str, Any]] = []
        for index, character in enumerate(stripped):
            if character != "{":
                continue
            try:
                candidate, end = decoder.raw_decode(stripped[index:])
            except json.JSONDecodeError:
                continue
            if stripped[index + end :].strip():
                continue
            if isinstance(candidate, dict) and set(candidate) == REQUIRED_FIELDS:
                candidates.append(candidate)
        if len(candidates) != 1:
            raise ContractError(
                f"final response has no unique trailing JSON contract: {exc.msg}"
            ) from exc
        return candidates[0], "trailing-json-fallback"
    if not isinstance(data, dict):
        raise ContractError("final response must be a JSON object")
    return data, "exact-json"


def parse_worker_contract(text: str) -> WorkerContract:
    data, transport = _json_object_from_text(text)
    missing = REQUIRED_FIELDS - data.keys()
    unknown = data.keys() - REQUIRED_FIELDS
    if missing:
        raise ContractError(f"missing contract fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ContractError(f"unknown contract fields: {', '.join(sorted(unknown))}")

    status = str(data["status"]).lower()
    next_gate = str(data["next_gate"]).lower()
    if status not in ALLOWED_STATUSES:
        raise ContractError(f"unknown status: {status}")
    if next_gate not in ALLOWED_GATES:
        raise ContractError(f"unknown next_gate: {next_gate}")

    candidate = data["candidate"]
    if candidate is not None and not isinstance(candidate, dict):
        raise ContractError("candidate must be an object or null")
    if status == "done" and candidate is None:
        raise ContractError("done contract requires a candidate")
    if status == "done" and next_gate != "validate":
        raise ContractError("done contract must request the validate gate")

    summary = data["summary"]
    if not isinstance(summary, list) or not all(isinstance(item, str) for item in summary):
        raise ContractError("summary must be an array of strings")
    if len(summary) > 5:
        raise ContractError("summary must contain five or fewer items")

    lesson_data = data["lesson"]
    lesson: LessonProposal | None = None
    if lesson_data is not None:
        if not isinstance(lesson_data, dict):
            raise ContractError("lesson must be an object or null")
        if set(lesson_data) != {"statement", "tags", "evidence"}:
            raise ContractError("lesson requires exactly statement, tags, and evidence")
        tags = lesson_data["tags"]
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ContractError("lesson tags must be an array of strings")
        lesson = LessonProposal(
            statement=str(lesson_data["statement"]).strip(),
            tags=tuple(tag.strip() for tag in tags if tag.strip()),
            evidence=str(lesson_data["evidence"]).strip(),
        )
        if not lesson.statement or not lesson.evidence:
            raise ContractError("lesson statement and evidence must be non-empty")

    return WorkerContract(
        status=status,
        candidate=candidate,
        lesson=lesson,
        summary=tuple(summary),
        next_gate=next_gate,
        transport=transport,
    )

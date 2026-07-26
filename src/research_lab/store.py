from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import fcntl

from .domain import Lesson


class ResearchStore(Protocol):
    def create_run(self, run_id: str, manifest: dict[str, Any]) -> None: ...

    def read_run_manifest(self, run_id: str) -> dict[str, Any]: ...

    def append_lifecycle_event(
        self,
        run_id: str,
        attempt_id: str,
        event: dict[str, Any],
    ) -> None: ...

    def append_attempt(self, run_id: str, attempt: dict[str, Any]) -> None: ...

    def list_attempts(self, run_id: str) -> list[dict[str, Any]]: ...

    def list_lifecycle_events(
        self,
        run_id: str,
        attempt_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_validated_lesson(self, lesson: Lesson) -> None: ...

    def find_lessons(self, tags: tuple[str, ...], limit: int = 3) -> list[Lesson]: ...

    def write_report(self, run_id: str, report: str) -> Path: ...


def _atomic_write_text(path: Path, text: str) -> None:
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


def _write_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


class FileResearchStore:
    """Single-controller storage with atomic immutable attempt writes."""

    def __init__(self, root: Path):
        self.root = root
        self._validated_lessons: list[Lesson] | None = None

    def create_run(self, run_id: str, manifest: dict[str, Any]) -> None:
        run_path = self.root / "runs" / run_id
        if run_path.exists():
            raise FileExistsError(f"run already exists: {run_id}")
        (run_path / "attempts").mkdir(parents=True)
        (run_path / "lifecycle").mkdir(parents=True)
        _write_json(run_path / "manifest.json", manifest)

    def read_run_manifest(self, run_id: str) -> dict[str, Any]:
        path = self.root / "runs" / run_id / "manifest.json"
        if not path.exists():
            raise FileNotFoundError(f"run does not exist: {run_id}")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"run manifest is not an object: {run_id}")
        return value

    @contextmanager
    def controller_lock(self) -> Iterator[None]:
        """Prevent two controller processes from sharing one file-store root."""
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / ".controller.lock"
        with path.open("a+", encoding="utf-8") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError(
                    f"another controller owns file store {self.root}"
                ) from exc
            handle.seek(0)
            handle.truncate()
            handle.write(f"pid={os.getpid()}\n")
            handle.flush()
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def append_lifecycle_event(
        self,
        run_id: str,
        attempt_id: str,
        event: dict[str, Any],
    ) -> None:
        event_id = str(event["id"])
        path = (
            self.root
            / "runs"
            / run_id
            / "lifecycle"
            / attempt_id
            / f"{event_id}.json"
        )
        if path.exists():
            return
        _write_json(path, event)

    def append_attempt(self, run_id: str, attempt: dict[str, Any]) -> None:
        attempt_id = str(attempt["id"])
        path = self.root / "runs" / run_id / "attempts" / f"{attempt_id}.json"
        if path.exists():
            raise FileExistsError(f"attempt already exists: {attempt_id}")
        _write_json(path, attempt)

    def list_attempts(self, run_id: str) -> list[dict[str, Any]]:
        attempt_dir = self.root / "runs" / run_id / "attempts"
        if not attempt_dir.exists():
            return []
        records = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(attempt_dir.glob("*.json"))
        ]
        return sorted(records, key=lambda record: int(record["sequence"]))

    def list_lifecycle_events(
        self,
        run_id: str,
        attempt_id: str | None = None,
    ) -> list[dict[str, Any]]:
        directory = self.root / "runs" / run_id / "lifecycle"
        if attempt_id is not None:
            directories = [directory / attempt_id]
        elif directory.exists():
            directories = sorted(path for path in directory.iterdir() if path.is_dir())
        else:
            directories = []
        records: list[dict[str, Any]] = []
        for attempt_directory in directories:
            for path in sorted(attempt_directory.glob("*.json")):
                value = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(value, dict):
                    raise ValueError(f"lifecycle event is not an object: {path}")
                records.append(value)
        return sorted(
            records,
            key=lambda record: (
                str(record.get("attempt_id", "")),
                str(record.get("id", "")),
            ),
        )

    def save_validated_lesson(self, lesson: Lesson) -> None:
        path = self.root / "lessons" / "validated" / f"{lesson.id}.json"
        if path.exists():
            return
        _write_json(path, lesson.to_dict())
        if self._validated_lessons is not None:
            self._validated_lessons.append(lesson)

    def find_lessons(self, tags: tuple[str, ...], limit: int = 3) -> list[Lesson]:
        if self._validated_lessons is None:
            self._validated_lessons = self._load_validated_lessons()
        requested = set(tags)
        ranked: list[tuple[int, Lesson]] = []
        for lesson in self._validated_lessons:
            overlap = len(requested.intersection(lesson.tags))
            if overlap:
                ranked.append((overlap, lesson))
        ranked.sort(key=lambda item: (-item[0], item[1].id))
        return [lesson for _, lesson in ranked[:limit]]

    def _load_validated_lessons(self) -> list[Lesson]:
        directory = self.root / "lessons" / "validated"
        if not directory.exists():
            return []
        lessons: list[Lesson] = []
        for path in sorted(directory.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            lessons.append(
                Lesson(
                    id=str(data["id"]),
                    statement=str(data["statement"]),
                    tags=tuple(str(tag) for tag in data["tags"]),
                    evidence=str(data["evidence"]),
                    source_run_id=str(data["source_run_id"]),
                    source_attempt_id=str(data["source_attempt_id"]),
                    source_task_id=str(data["source_task_id"]),
                    created_at=str(data["created_at"]),
                )
            )
        return lessons

    def write_report(self, run_id: str, report: str) -> Path:
        path = self.root / "runs" / run_id / "report.md"
        _atomic_write_text(path, report.rstrip() + "\n")
        return path

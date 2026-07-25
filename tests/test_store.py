import tempfile
import unittest
from pathlib import Path

from research_lab.domain import Lesson
from research_lab.store import FileResearchStore


class FileResearchStoreTests(unittest.TestCase):
    def test_attempts_are_immutable_and_lessons_are_retrievable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = FileResearchStore(Path(directory))
            store.create_run("run-1", {"id": "run-1"})
            store.append_lifecycle_event(
                "run-1",
                "attempt-1",
                {"id": "0001-selected", "kind": "attempt_selected"},
            )
            self.assertTrue(
                (
                    Path(directory)
                    / "runs"
                    / "run-1"
                    / "lifecycle"
                    / "attempt-1"
                    / "0001-selected.json"
                ).exists()
            )
            store.append_attempt(
                "run-1",
                {"id": "attempt-1", "sequence": 1, "task_id": "task-1"},
            )
            self.assertEqual(store.list_attempts("run-1")[0]["id"], "attempt-1")
            with self.assertRaises(FileExistsError):
                store.append_attempt(
                    "run-1",
                    {"id": "attempt-1", "sequence": 1, "task_id": "task-1"},
                )

            lesson = Lesson(
                id="lesson-1",
                statement="Use constrained nodes first.",
                tags=("graph-coloring", "sparse"),
                evidence="validated",
                source_run_id="run-1",
                source_attempt_id="attempt-1",
                source_task_id="task-1",
                created_at="2026-07-25T00:00:00+00:00",
            )
            store.save_validated_lesson(lesson)
            results = store.find_lessons(("graph-coloring",), limit=3)
            self.assertEqual([item.id for item in results], ["lesson-1"])


if __name__ == "__main__":
    unittest.main()

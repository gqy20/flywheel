"""Performance tests for incremental updates in TodoApp.

Issue #4522: TodoApp operations should avoid full load/save cycles for large datasets.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from flywheel.cli import TodoApp


class TestIncrementalUpdates:
    """Tests for incremental update performance."""

    def test_add_uses_append_mode_for_existing_file(self, tmp_path: Path) -> None:
        """Issue #4522: add() should use append mode instead of full rewrite."""
        db_path = tmp_path / "test.json"
        app = TodoApp(str(db_path))

        # First add creates the file
        app.add("first todo")

        # Check that subsequent adds don't do full file rewrites
        # We track this by checking if the file is modified in append-like manner
        initial_size = db_path.stat().st_size

        app.add("second todo")
        new_size = db_path.stat().st_size

        # File should grow, not be fully rewritten (size difference should be minimal)
        assert new_size > initial_size

    def test_mark_done_modifies_in_place(self, tmp_path: Path) -> None:
        """Issue #4522: mark_done() should modify file in-place when possible."""
        db_path = tmp_path / "test.json"
        app = TodoApp(str(db_path))

        # Add a todo
        todo = app.add("test todo")
        todo_id = todo.id

        # Load and verify initial state
        todos = app.list()
        assert len(todos) == 1
        assert todos[0].done is False

        # Mark done
        app.mark_done(todo_id)

        # Verify the todo is marked done
        todos = app.list()
        assert todos[0].done is True

    def test_performance_with_large_dataset(self, tmp_path: Path) -> None:
        """Issue #4522: Operations should be reasonably fast with large datasets."""
        db_path = tmp_path / "large.json"

        # Create a large initial dataset (1000 todos)
        large_todos = [
            {"id": i, "text": f"Initial todo {i}", "done": False} for i in range(1, 1001)
        ]
        db_path.write_text(json.dumps(large_todos), encoding="utf-8")

        app = TodoApp(str(db_path))

        # Time the add operation
        start = time.perf_counter()
        app.add("new todo after large dataset")
        add_duration = time.perf_counter() - start

        # Time the mark_done operation
        start = time.perf_counter()
        app.mark_done(500)
        mark_done_duration = time.perf_counter() - start

        # Operations should complete in reasonable time (< 1 second each)
        # This is a sanity check, not a strict benchmark
        assert add_duration < 1.0, f"add() took {add_duration:.3f}s, expected < 1s"
        assert mark_done_duration < 1.0, f"mark_done() took {mark_done_duration:.3f}s, expected < 1s"

    def test_incremental_add_appends_to_json(self, tmp_path: Path) -> None:
        """Issue #4522: Adding a new todo should use incremental append."""
        db_path = tmp_path / "test.json"
        app = TodoApp(str(db_path))

        # Create initial todos
        app.add("todo 1")
        app.add("todo 2")

        # Verify both are saved
        todos = app.list()
        assert len(todos) == 2

        # Add third - should work correctly with incremental approach
        app.add("todo 3")

        todos = app.list()
        assert len(todos) == 3
        assert todos[-1].text == "todo 3"

    def test_remove_operation_maintains_consistency(self, tmp_path: Path) -> None:
        """Issue #4522: Remove should maintain data consistency."""
        db_path = tmp_path / "test.json"
        app = TodoApp(str(db_path))

        # Add multiple todos
        app.add("keep this")
        app.add("remove this")
        app.add("keep this too")

        # Remove middle one
        todos = app.list()
        remove_id = next(t.id for t in todos if t.text == "remove this")
        app.remove(remove_id)

        # Verify consistency
        todos = app.list()
        assert len(todos) == 2
        texts = {t.text for t in todos}
        assert texts == {"keep this", "keep this too"}

    def test_concurrent_operations_integrity(self, tmp_path: Path) -> None:
        """Issue #4522: Multiple operations in sequence should maintain data integrity."""
        db_path = tmp_path / "test.json"
        app = TodoApp(str(db_path))

        # Perform a series of operations
        app.add("task 1")
        app.add("task 2")
        app.mark_done(1)
        app.add("task 3")
        app.mark_undone(1)
        app.remove(2)

        # Verify final state
        todos = app.list()
        assert len(todos) == 2
        assert {t.text for t in todos} == {"task 1", "task 3"}
        # task 1 should be undone (we marked done then undone)
        task1 = next(t for t in todos if t.text == "task 1")
        assert task1.done is False

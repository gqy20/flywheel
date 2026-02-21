"""Tests for issue #5029: next_id returns duplicate IDs when todo list has non-contiguous IDs.

This test suite verifies that next_id returns the first available gap when IDs are
non-contiguous, preventing duplicate IDs after removal operations.

Acceptance criteria:
- After removing todo #2 from [1,2,3], next_id should return 2 (first available), not 4
- No two todos should ever have the same ID
- IDs remain stable across save/load cycles
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdNonContiguous:
    """Test suite for next_id with non-contiguous IDs."""

    def test_next_id_returns_gap_after_middle_removal(self, tmp_path: Path) -> None:
        """Test that next_id returns 2 after removing todo #2 from [1,2,3]."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create todos with IDs [1, 2, 3]
        todos = [
            Todo(id=1, text="first"),
            Todo(id=2, text="second"),
            Todo(id=3, text="third"),
        ]

        # After removing #2, next_id should return 2 (the gap), not 4
        todos_after_removal = [t for t in todos if t.id != 2]
        next_id = storage.next_id(todos_after_removal)

        assert next_id == 2, f"Expected next_id=2 for gap in [1,3], got {next_id}"

    def test_next_id_finds_first_gap_in_non_contiguous_list(self, tmp_path: Path) -> None:
        """Test that next_id finds first gap in [1, 3, 5]."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create todos with non-contiguous IDs [1, 3, 5]
        todos = [
            Todo(id=1, text="first"),
            Todo(id=3, text="third"),
            Todo(id=5, text="fifth"),
        ]

        # next_id should return 2 (first available gap), not 6
        next_id = storage.next_id(todos)

        assert next_id == 2, f"Expected next_id=2 for gap in [1,3,5], got {next_id}"

    def test_next_id_no_duplicate_after_removal(self, tmp_path: Path) -> None:
        """Test that adding after removal doesn't create duplicate IDs."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create and save todos [1, 2, 3]
        todos = [
            Todo(id=1, text="first"),
            Todo(id=2, text="second"),
            Todo(id=3, text="third"),
        ]
        storage.save(todos)

        # Simulate removal of todo #2 (like app.remove would do)
        loaded = storage.load()
        loaded = [t for t in loaded if t.id != 2]
        storage.save(loaded)

        # Get next_id and add new todo
        reloaded = storage.load()
        new_id = storage.next_id(reloaded)

        # New ID should be 2, filling the gap
        assert new_id == 2, f"Expected next_id=2 after removing #2, got {new_id}"

        # Verify no duplicate when we add the new todo
        new_todo = Todo(id=new_id, text="new task")
        reloaded.append(new_todo)

        # Check all IDs are unique
        all_ids = [t.id for t in reloaded]
        assert len(all_ids) == len(set(all_ids)), f"Duplicate IDs found: {all_ids}"

    def test_next_id_empty_list_returns_one(self, tmp_path: Path) -> None:
        """Test that next_id returns 1 for empty list."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        next_id = storage.next_id([])

        assert next_id == 1, f"Expected next_id=1 for empty list, got {next_id}"

    def test_next_id_contiguous_returns_next(self, tmp_path: Path) -> None:
        """Test that next_id returns max+1 for contiguous IDs."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create contiguous todos [1, 2, 3]
        todos = [
            Todo(id=1, text="first"),
            Todo(id=2, text="second"),
            Todo(id=3, text="third"),
        ]

        next_id = storage.next_id(todos)

        # For contiguous [1,2,3], next should be 4
        assert next_id == 4, f"Expected next_id=4 for contiguous [1,2,3], got {next_id}"

    def test_next_id_multiple_gaps_finds_first(self, tmp_path: Path) -> None:
        """Test that next_id finds first gap when multiple exist."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create todos with multiple gaps: [2, 5, 8]
        # Gaps: 1, 3, 4, 6, 7 - should return 1 (first gap)
        todos = [
            Todo(id=2, text="second"),
            Todo(id=5, text="fifth"),
            Todo(id=8, text="eighth"),
        ]

        next_id = storage.next_id(todos)

        assert next_id == 1, f"Expected next_id=1 for first gap in [2,5,8], got {next_id}"

    def test_integration_add_after_remove_no_duplicate(self, tmp_path: Path) -> None:
        """Integration test: verify CLI-style add after remove produces no duplicates."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Initial state: [1, 2, 3]
        todos = [
            Todo(id=1, text="task one"),
            Todo(id=2, text="task two"),
            Todo(id=3, text="task three"),
        ]
        storage.save(todos)

        # Remove #2 (simulate app.remove behavior)
        loaded = storage.load()
        remaining = [t for t in loaded if t.id != 2]
        storage.save(remaining)

        # Add new todo (simulate app.add behavior)
        reloaded = storage.load()
        new_id = storage.next_id(reloaded)
        new_todo = Todo(id=new_id, text="new task")
        reloaded.append(new_todo)
        storage.save(reloaded)

        # Load final state and verify
        final = storage.load()
        final_ids = sorted([t.id for t in final])

        # Should have [1, 2, 3] (new todo got ID 2)
        assert final_ids == [1, 2, 3], f"Expected [1, 2, 3], got {final_ids}"

        # All IDs should be unique
        assert len(final_ids) == len(set(final_ids)), f"Duplicate IDs: {final_ids}"

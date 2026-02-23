"""Regression test for issue #5388: next_id should return positive integers only.

Issue: next_id could return negative values or duplicate IDs when the todos list
contains negative IDs or non-contiguous IDs.

Fix: Filter out non-positive IDs before calculating max, ensuring next_id
always returns a positive integer.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdWithNegativeIds:
    """Tests for next_id behavior when todos contain negative or non-standard IDs."""

    def test_next_id_with_single_negative_id_returns_positive(self, tmp_path: Path) -> None:
        """When todos list contains only negative IDs, next_id should return 1.

        Regression test for issue #5388.
        Before fix: max([-5]) + 1 = -4
        After fix: max([]) + 1 = 1 (filtering out negative IDs)
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a todo with a negative ID (simulating manually edited JSON)
        todos = [Todo(id=-5, text="negative id todo")]

        # next_id should return 1, not -4 or 0
        next_id = storage.next_id(todos)
        assert next_id == 1, f"Expected next_id=1 for todos with only negative IDs, got {next_id}"
        assert next_id > 0, "next_id must return a positive integer"

    def test_next_id_with_mixed_positive_and_negative_ids(self, tmp_path: Path) -> None:
        """When todos list contains both positive and negative IDs, next_id should use max positive ID + 1.

        Regression test for issue #5388.
        Before fix: max([-1, 2]) + 1 = 3 (correct by accident, but relied on positive max)
        After fix: max([2]) + 1 = 3 (filtering out negative IDs explicitly)
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Mix of negative and positive IDs
        todos = [Todo(id=-1, text="negative id"), Todo(id=2, text="positive id")]

        # next_id should return 3 (max positive ID + 1), not 0 or negative
        next_id = storage.next_id(todos)
        assert next_id == 3, f"Expected next_id=3 for todos with IDs [-1, 2], got {next_id}"
        assert next_id > 0, "next_id must return a positive integer"

    def test_next_id_with_zero_id_uses_max_positive(self, tmp_path: Path) -> None:
        """When todos list contains ID=0, it should be ignored as non-positive.

        Regression test for issue #5388.
        Zero is not a valid positive ID, so it should be filtered out.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Include ID=0 which is non-positive
        todos = [Todo(id=0, text="zero id"), Todo(id=5, text="positive id")]

        # next_id should return 6 (max positive ID + 1), not 1
        next_id = storage.next_id(todos)
        assert next_id == 6, f"Expected next_id=6 for todos with IDs [0, 5], got {next_id}"
        assert next_id > 0, "next_id must return a positive integer"

    def test_next_id_with_only_zero_ids_returns_one(self, tmp_path: Path) -> None:
        """When todos list contains only zero IDs, next_id should return 1."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Only zero IDs
        todos = [Todo(id=0, text="zero id 1"), Todo(id=0, text="zero id 2")]

        # next_id should return 1 since no positive IDs exist
        next_id = storage.next_id(todos)
        assert next_id == 1, f"Expected next_id=1 for todos with only zero IDs, got {next_id}"

    def test_next_id_with_empty_list_returns_one(self, tmp_path: Path) -> None:
        """When todos list is empty, next_id should return 1.

        This is existing behavior that should be preserved.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Empty list
        todos: list[Todo] = []

        # next_id should return 1
        next_id = storage.next_id(todos)
        assert next_id == 1, f"Expected next_id=1 for empty list, got {next_id}"

    def test_next_id_with_only_positive_ids_increments_max(self, tmp_path: Path) -> None:
        """When todos list contains only positive IDs, next_id should return max + 1.

        This is existing behavior that should be preserved.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Only positive IDs
        todos = [Todo(id=1, text="first"), Todo(id=3, text="second"), Todo(id=5, text="third")]

        # next_id should return 6 (max ID + 1)
        next_id = storage.next_id(todos)
        assert next_id == 6, f"Expected next_id=6 for todos with IDs [1, 3, 5], got {next_id}"

    def test_next_id_never_returns_negative_or_zero(self, tmp_path: Path) -> None:
        """Comprehensive test: next_id should never return negative or zero values.

        This tests various edge cases to ensure next_id always returns a positive integer.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Test various combinations that could lead to negative results
        test_cases = [
            ([Todo(id=-10, text="x")], "only negative"),
            ([Todo(id=-1, text="x")], "single negative"),
            ([Todo(id=-100, text="x"), Todo(id=-1, text="y")], "multiple negatives"),
            ([Todo(id=0, text="x")], "zero only"),
            ([Todo(id=-5, text="x"), Todo(id=0, text="y")], "negative and zero"),
        ]

        for todos, description in test_cases:
            next_id = storage.next_id(todos)
            assert next_id > 0, f"next_id returned {next_id} for {description}, expected positive integer"

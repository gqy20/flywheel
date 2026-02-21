"""Tests for unique ID validation (Issue #4398).

These tests verify that:
1. next_id returns an ID that doesn't conflict with any existing IDs
2. load() detects and raises error when JSON contains duplicate IDs
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


class TestNextIdWithNonContiguousIds:
    """Test that next_id returns unique IDs even with gaps in existing IDs."""

    def test_next_id_returns_unique_id_with_gaps(self, tmp_path) -> None:
        """next_id should return the smallest available ID that doesn't conflict.

        This is the core fix: when there are gaps like [1, 3, 5], next_id
        should return 2 (the smallest unused ID), not 6 (max+1).
        This prevents ID conflicts if the JSON file was manually edited.
        """
        db = tmp_path / "todos.json"
        storage = TodoStorage(str(db))

        # Create todos with non-contiguous IDs (1, 3, 5)
        db.write_text(
            '[{"id": 1, "text": "task1"}, {"id": 3, "text": "task3"}, {"id": 5, "text": "task5"}]',
            encoding="utf-8",
        )

        todos = storage.load()
        new_id = storage.next_id(todos)
        existing_ids = {todo.id for todo in todos}

        # The new ID should not conflict with any existing ID
        assert new_id not in existing_ids, (
            f"next_id returned {new_id} which conflicts with existing IDs {existing_ids}"
        )

    def test_next_id_with_all_ids_from_1_to_n(self, tmp_path) -> None:
        """When IDs are contiguous from 1 to N, next_id should return N+1."""
        db = tmp_path / "todos.json"
        storage = TodoStorage(str(db))

        # Create todos with contiguous IDs (1, 2, 3)
        db.write_text(
            '[{"id": 1, "text": "a"}, {"id": 2, "text": "b"}, {"id": 3, "text": "c"}]',
            encoding="utf-8",
        )

        todos = storage.load()
        new_id = storage.next_id(todos)

        assert new_id == 4


class TestLoadDetectsDuplicateIds:
    """Test that load() detects and raises error for duplicate IDs in JSON."""

    def test_load_raises_error_on_duplicate_ids(self, tmp_path) -> None:
        """load() should raise ValueError when JSON contains duplicate IDs.

        This prevents data corruption from manual edits or external tools.
        """
        db = tmp_path / "duplicate.json"
        storage = TodoStorage(str(db))

        # Create JSON with duplicate ID 1
        db.write_text(
            '[{"id": 1, "text": "first"}, {"id": 1, "text": "duplicate"}]',
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match=r"duplicate|unique|id"):
            storage.load()

    def test_load_accepts_unique_ids(self, tmp_path) -> None:
        """load() should accept JSON with all unique IDs."""
        db = tmp_path / "valid.json"
        storage = TodoStorage(str(db))

        # Create JSON with unique IDs
        db.write_text(
            '[{"id": 1, "text": "first"}, {"id": 2, "text": "second"}]',
            encoding="utf-8",
        )

        todos = storage.load()
        assert len(todos) == 2
        assert {todo.id for todo in todos} == {1, 2}

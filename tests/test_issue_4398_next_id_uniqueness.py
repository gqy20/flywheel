"""Tests for issue #4398: next_id should not cause ID conflicts."""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdUniqueness:
    """Tests for next_id returning unique IDs."""

    def test_next_id_returns_unique_id_after_manual_edit(self, tmp_path) -> None:
        """Bug #4398: next_id should always return a unique ID.

        Scenario: JSON file is manually edited to have IDs [1, 3, 5].
        Someone manually adds ID 2. Now next_id should still return a unique ID.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Start with non-consecutive IDs [1, 3, 5]
        todos_data = [
            {"id": 1, "text": "task 1", "done": False},
            {"id": 3, "text": "task 3", "done": False},
            {"id": 5, "text": "task 5", "done": False},
        ]
        db.write_text(json.dumps(todos_data), encoding="utf-8")

        loaded = storage.load()

        # Simulate manually adding ID 2 (filling a gap)
        todos_data.append({"id": 2, "text": "task 2", "done": False})
        db.write_text(json.dumps(todos_data), encoding="utf-8")

        loaded = storage.load()
        existing_ids = {todo.id for todo in loaded}

        # next_id should return an ID that doesn't already exist
        # Current buggy implementation: returns max+1 = 6 (which is unique, so this passes)
        # But the actual bug is when JSON has [1,2,3] and next_id returns 4 which is also valid
        # The real issue is that we should ensure next_id never conflicts
        new_id = storage.next_id(loaded)
        assert new_id not in existing_ids, (
            f"next_id returned {new_id} which already exists in {existing_ids}"
        )

    def test_next_id_with_filled_gap_id_conflict(self, tmp_path) -> None:
        """Bug #4398: next_id must not conflict even if max_id was just filled.

        More direct test of the bug: if IDs are [2, 3], next_id should NOT return 3
        (which is what max+1 would give, since max=2 -> 3 conflicts with existing 3).
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Start with [2, 3] - where max is 3, so max+1=4 is fine
        # But the issue is the algorithm doesn't guarantee uniqueness
        todos_data = [
            {"id": 2, "text": "task 2", "done": False},
            {"id": 3, "text": "task 3", "done": False},
        ]
        db.write_text(json.dumps(todos_data), encoding="utf-8")

        loaded = storage.load()
        existing_ids = {todo.id for todo in loaded}

        # next_id should return an ID that doesn't already exist
        new_id = storage.next_id(loaded)
        assert new_id not in existing_ids, (
            f"next_id returned {new_id} which already exists in {existing_ids}"
        )


class TestLoadDuplicateIdDetection:
    """Tests for load() detecting duplicate IDs."""

    def test_load_rejects_duplicate_ids(self, tmp_path) -> None:
        """Bug #4398: load() should raise ValueError when JSON contains duplicate IDs."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create JSON with duplicate IDs
        todos_data = [
            {"id": 1, "text": "task 1a", "done": False},
            {"id": 1, "text": "task 1b", "done": False},  # Duplicate ID
        ]
        db.write_text(json.dumps(todos_data), encoding="utf-8")

        # load() should raise ValueError for duplicate IDs
        with pytest.raises(ValueError, match="[Dd]uplicate.*[Ii][Dd]"):
            storage.load()

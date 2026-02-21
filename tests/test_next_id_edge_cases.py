"""Tests for next_id() edge cases in TodoStorage.

This test suite covers edge cases that were previously untested:
- Gap IDs: [1, 5, 10] -> should return 11 (max + 1)
- Single high ID: [Todo(id=100)] -> should return 101
- Empty list: [] -> should return 1
- Duplicate IDs in JSON file load()
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdEdgeCases:
    """Tests for next_id() with various edge cases."""

    def test_next_id_with_gap_ids(self) -> None:
        """Test next_id() returns correct value when there are gaps in IDs.

        The function should return max(id) + 1, not fill gaps.
        For [1, 5, 10], it should return 11.
        """
        todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=10, text="c")]
        storage = TodoStorage(":memory:")  # Path doesn't matter for this test
        assert storage.next_id(todos) == 11

    def test_next_id_with_single_high_id(self) -> None:
        """Test next_id() with a single high ID value.

        For [Todo(id=100)], it should return 101.
        """
        todos = [Todo(id=100, text="high id")]
        storage = TodoStorage(":memory:")
        assert storage.next_id(todos) == 101

    def test_next_id_with_empty_list(self) -> None:
        """Test next_id() with empty list returns 1."""
        storage = TodoStorage(":memory:")
        assert storage.next_id([]) == 1

    def test_next_id_with_negative_ids(self) -> None:
        """Test next_id() handles negative IDs correctly.

        Even with negative IDs, it should return max(id) + 1.
        If max is negative (-1), result would be 0.
        """
        todos = [Todo(id=-5, text="negative"), Todo(id=-1, text="less negative")]
        storage = TodoStorage(":memory:")
        # max(-5, -1) + 1 = 0
        assert storage.next_id(todos) == 0

    def test_next_id_after_removing_middle_item(self) -> None:
        """Test next_id() after removing a middle item (creating a gap).

        If we have [1, 2, 3] and remove 2, we get [1, 3].
        next_id should still return 4 (max + 1), not 2.
        """
        todos = [Todo(id=1, text="first"), Todo(id=3, text="third")]
        storage = TodoStorage(":memory:")
        assert storage.next_id(todos) == 4


class TestLoadWithDuplicateIds:
    """Tests for load() with duplicate IDs in JSON file."""

    def test_load_with_duplicate_ids_returns_both_items(self, tmp_path) -> None:
        """Test that load() returns all items even with duplicate IDs.

        The storage layer does not enforce ID uniqueness during load.
        Both items with id=1 should be loaded.
        """
        db = tmp_path / "duplicate_ids.json"
        storage = TodoStorage(str(db))

        # Create JSON with duplicate IDs
        data = [
            {"id": 1, "text": "first item", "done": False},
            {"id": 1, "text": "second item with same id", "done": True},
        ]
        db.write_text(json.dumps(data), encoding="utf-8")

        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].id == 1
        assert loaded[0].text == "first item"
        assert loaded[1].id == 1
        assert loaded[1].text == "second item with same id"

    def test_load_with_multiple_duplicate_ids(self, tmp_path) -> None:
        """Test load() with multiple sets of duplicate IDs."""
        db = tmp_path / "multiple_duplicates.json"
        storage = TodoStorage(str(db))

        # Create JSON with multiple duplicates
        data = [
            {"id": 1, "text": "item 1a"},
            {"id": 1, "text": "item 1b"},
            {"id": 2, "text": "item 2a"},
            {"id": 2, "text": "item 2b"},
            {"id": 5, "text": "item 5"},
        ]
        db.write_text(json.dumps(data), encoding="utf-8")

        loaded = storage.load()
        assert len(loaded) == 5
        # Verify all items are loaded
        assert [t.id for t in loaded] == [1, 1, 2, 2, 5]

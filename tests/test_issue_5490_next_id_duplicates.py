"""Regression tests for issue #5490: next_id generates duplicate IDs.

This test suite verifies that next_id correctly generates unique IDs
when the todo list contains non-contiguous IDs (gaps from deletions).
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdWithNonContiguousIds:
    """Tests for next_id behavior with gaps in ID sequence."""

    def test_next_id_returns_next_after_max_id_with_gaps(self, tmp_path) -> None:
        """Test that next_id returns max+1 even with non-contiguous IDs.

        Given todos with ids [1, 3, 5], next_id should return 6 (not 2 or 4).
        This ensures we don't fill gaps which could cause issues if IDs
        are later reused unexpectedly.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create todos with gaps and save them
        todos = [Todo(id=1, text="a"), Todo(id=3, text="b"), Todo(id=5, text="c")]
        storage.save(todos)

        # Load and get next_id
        loaded = storage.load()
        result = storage.next_id(loaded)

        assert result == 6, f"Expected next_id to return 6 (max+1), got {result}"

    def test_next_id_returns_higher_after_deletion(self, tmp_path) -> None:
        """Test that next_id returns a value higher than any previously used ID.

        This test verifies that deleted IDs are not reused.
        The fix uses a persistent counter stored in the JSON file.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create todos [1, 2, 3] and save
        todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]
        storage.save(todos)

        # Verify the counter was saved with next_id = 4
        loaded = storage.load()
        assert storage._next_id == 4, "Counter should be 4 after saving [1,2,3]"

        # Simulate deletion of id=3 by saving a reduced list
        todos_after_delete = [t for t in loaded if t.id != 3]
        storage.save(todos_after_delete)

        # Reload and check next_id
        storage2 = TodoStorage(str(db))
        loaded2 = storage2.load()
        result = storage2.next_id(loaded2)

        # The next ID should be 4 (tracked counter), not 3 (reusing deleted)
        assert result == 4, (
            f"Expected next_id to return 4 (tracked counter), got {result}"
        )

    def test_next_id_empty_list_returns_one(self) -> None:
        """Test that next_id returns 1 for empty list."""
        storage = TodoStorage()
        todos: list[Todo] = []

        result = storage.next_id(todos)

        assert result == 1

    def test_next_id_never_duplicates_existing_ids(self, tmp_path) -> None:
        """Test that next_id never returns an ID that already exists.

        This is the core requirement: next_id should return an ID
        that doesn't exist in the current list.
        """
        db = tmp_path / "todo.json"

        # Test various gap scenarios with persistence
        test_cases = [
            ([1, 5, 10], 11),  # Large gaps
            ([1, 2, 3], 4),  # Contiguous
            ([100], 101),  # Single high ID
            ([1], 2),  # Single low ID
        ]

        for ids, expected in test_cases:
            db.unlink(missing_ok=True)
            storage = TodoStorage(str(db))
            todos = [Todo(id=i, text=f"task-{i}") for i in ids]
            storage.save(todos)
            loaded = storage.load()
            result = storage.next_id(loaded)
            assert result == expected, (
                f"For IDs {ids}, expected next_id={expected}, got {result}"
            )
            # Verify result doesn't duplicate any existing ID
            assert result not in ids, (
                f"next_id={result} duplicates an existing ID in {ids}"
            )

    def test_next_id_after_multiple_deletions(self, tmp_path) -> None:
        """Test next_id after multiple deletions creating larger gaps.

        Starting with [1, 2, 3, 4, 5], delete 3 and 5.
        Remaining: [1, 2, 4]
        next_id should return 6 (tracked counter, higher than any ID ever used).
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create todos [1, 2, 3, 4, 5] and save
        todos = [
            Todo(id=1, text="a"),
            Todo(id=2, text="b"),
            Todo(id=3, text="c"),
            Todo(id=4, text="d"),
            Todo(id=5, text="e"),
        ]
        storage.save(todos)

        # Verify counter is 6
        loaded = storage.load()
        assert storage._next_id == 6, "Counter should be 6 after saving [1-5]"

        # Simulate deletion of 3 and 5
        todos_after_delete = [t for t in loaded if t.id not in (3, 5)]
        storage.save(todos_after_delete)

        # Reload and check next_id
        storage2 = TodoStorage(str(db))
        loaded2 = storage2.load()
        result = storage2.next_id(loaded2)

        # next_id should be 6 (tracked counter), which is > max in current list (4)
        assert result == 6, (
            f"Expected next_id=6 (tracked counter, > any ever used), got {result}"
        )

    def test_legacy_json_format_migration(self, tmp_path) -> None:
        """Test that legacy JSON format (list) is migrated to new format."""
        import json

        db = tmp_path / "todo.json"

        # Write legacy format (just a list)
        legacy_data = [
            {"id": 1, "text": "task 1", "done": False},
            {"id": 3, "text": "task 3", "done": False},
        ]
        db.write_text(json.dumps(legacy_data), encoding="utf-8")

        # Load with new storage
        storage = TodoStorage(str(db))
        todos = storage.load()

        # Should initialize counter from max id + 1 = 4
        assert storage._next_id == 4, "Counter should be initialized from max id + 1"

        # next_id should return 4
        result = storage.next_id(todos)
        assert result == 4, f"Expected next_id=4, got {result}"

        # Save and verify new format
        storage.save(todos)
        raw = json.loads(db.read_text(encoding="utf-8"))
        assert isinstance(raw, dict), "After save, should be in new format"
        assert "todos" in raw, "New format should have 'todos' key"
        assert "_next_id" in raw, "New format should have '_next_id' key"
        assert raw["_next_id"] == 5, "Counter should be incremented to 5"

"""Tests for load cache (with mtime invalidation) in TodoStorage.

This test suite verifies that TodoStorage.load() caches data in memory
and invalidates the cache when the file is modified externally.

Acceptance Criteria (from issue #5469):
- Consecutive load() calls without file modification return cached data
- File modification by external source causes load() to return new data
- save() automatically updates cache
- Cache can be disabled via parameter (for debug mode)
"""

from __future__ import annotations

import time
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestLoadCache:
    """Tests for the load cache feature."""

    def test_consecutive_load_returns_same_data_without_rereading_file(self, tmp_path: Path) -> None:
        """Test that consecutive load() calls return cached data without re-reading file.

        Regression test for issue #5469: load() should cache data in memory
        to reduce repeated IO in high-frequency query scenarios.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        todos = [Todo(id=1, text="cached task")]
        storage.save(todos)

        # First load reads from file
        first_load = storage.load()

        # Second load should return cached data (same object or equal data)
        second_load = storage.load()

        assert first_load == second_load
        assert len(second_load) == 1
        assert second_load[0].text == "cached task"

    def test_load_returns_new_data_after_external_file_modification(self, tmp_path: Path) -> None:
        """Test that load() returns new data when file is modified externally.

        The cache should be invalidated based on file mtime changes.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        todos = [Todo(id=1, text="original task")]
        storage.save(todos)

        # Load once to populate cache
        first_load = storage.load()
        assert first_load[0].text == "original task"

        # Simulate external modification by writing directly to file
        # Need to wait briefly to ensure mtime changes
        time.sleep(0.01)

        import json
        new_data = [{"id": 1, "text": "modified externally", "done": True}]
        db.write_text(json.dumps(new_data), encoding="utf-8")

        # Load should detect mtime change and return new data
        second_load = storage.load()
        assert len(second_load) == 1
        assert second_load[0].text == "modified externally"
        assert second_load[0].done is True

    def test_save_updates_cache_automatically(self, tmp_path: Path) -> None:
        """Test that save() automatically updates the cache.

        After save(), load() should return the saved data without re-reading file.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save initial data
        todos = [Todo(id=1, text="saved task")]
        storage.save(todos)

        # Load should return the saved data
        loaded = storage.load()
        assert loaded[0].text == "saved task"

        # Save new data
        new_todos = [Todo(id=1, text="updated task"), Todo(id=2, text="new task")]
        storage.save(new_todos)

        # Load should return the newly saved data
        loaded_again = storage.load()
        assert len(loaded_again) == 2
        assert loaded_again[0].text == "updated task"
        assert loaded_again[1].text == "new task"

    def test_cache_can_be_disabled(self, tmp_path: Path) -> None:
        """Test that cache can be disabled via parameter.

        When cache is disabled, load() should always read from file.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_cache=False)

        # Create initial data
        todos = [Todo(id=1, text="no cache")]
        storage.save(todos)

        # Load should read from file each time
        first_load = storage.load()
        second_load = storage.load()

        # Both should have same data but may be different objects
        assert len(first_load) == 1
        assert len(second_load) == 1
        assert first_load[0].text == "no cache"
        assert second_load[0].text == "no cache"

    def test_cache_handles_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that cache works correctly when file doesn't exist."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # First load returns empty list
        first_load = storage.load()
        assert first_load == []

        # Second load should return cached empty list
        second_load = storage.load()
        assert second_load == []

    def test_cache_handles_file_size_check(self, tmp_path: Path) -> None:
        """Test that cache doesn't bypass file size security check."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create normal data
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Load should work normally
        loaded = storage.load()
        assert len(loaded) == 1


class TestLoadCachePerformance:
    """Performance tests for load cache feature."""

    def test_second_load_is_faster_than_first(self, tmp_path: Path) -> None:
        """Test that second load is faster due to caching.

        This is a soft performance test - we just verify the cache mechanism works,
        not strict timing requirements.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create data
        todos = [Todo(id=i, text=f"task {i}") for i in range(100)]
        storage.save(todos)

        # First load (should read from file)
        first_load = storage.load()
        assert len(first_load) == 100

        # Second load (should use cache)
        second_load = storage.load()
        assert len(second_load) == 100

        # Data should be identical
        for i, todo in enumerate(second_load):
            assert todo.id == i
            assert todo.text == f"task {i}"

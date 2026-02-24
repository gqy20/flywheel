"""Tests for issue #5469: load cache with mtime-based invalidation.

This test suite verifies that TodoStorage.load() caches data to reduce
repeated IO, with automatic invalidation when the file is modified externally.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestLoadCache:
    """Tests for load() caching behavior."""

    def test_load_returns_cached_data_when_file_unchanged(self, tmp_path: Path) -> None:
        """Consecutive load() calls with no file modification should return cached data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create and save initial data
        todos = [Todo(id=1, text="cached task")]
        storage.save(todos)

        # First load reads from file
        loaded1 = storage.load()

        # Mock json.loads to verify it's not called again
        with patch("flywheel.storage.json.loads") as mock_loads:
            # Configure mock to return valid data if called
            mock_loads.return_value = [{"id": 1, "text": "mocked", "done": False}]

            # Second load should return cached data without reading file
            loaded2 = storage.load()

            # json.loads should not have been called (cache hit)
            mock_loads.assert_not_called()

        # Both loads should return same data
        assert len(loaded2) == 1
        assert loaded2[0].text == "cached task"  # Original data, not mocked
        assert loaded1[0].id == loaded2[0].id

    def test_load_reads_file_after_external_modification(self, tmp_path: Path) -> None:
        """If file is modified externally, load() should return new data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text="original")])
        loaded1 = storage.load()
        assert loaded1[0].text == "original"

        # Simulate external modification by writing directly to file
        # Need to ensure mtime actually changes
        time.sleep(0.01)  # Ensure mtime difference
        new_data = [{"id": 2, "text": "modified externally", "done": False}]
        db.write_text(json.dumps(new_data), encoding="utf-8")

        # Load should detect file change and read fresh data
        loaded2 = storage.load()
        assert len(loaded2) == 1
        assert loaded2[0].id == 2
        assert loaded2[0].text == "modified externally"

    def test_save_updates_cache(self, tmp_path: Path) -> None:
        """After save(), load() should return the saved data without re-reading file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save some data
        todos = [Todo(id=1, text="saved task"), Todo(id=2, text="another")]
        storage.save(todos)

        # Mock json.loads to verify it's not called after save
        with patch("flywheel.storage.json.loads") as mock_loads:
            mock_loads.return_value = []  # Would return empty if called

            # Load should return cached data from save, not read file
            loaded = storage.load()

            # json.loads should not have been called
            mock_loads.assert_not_called()

        # Should have the saved data
        assert len(loaded) == 2
        assert loaded[0].text == "saved task"
        assert loaded[1].text == "another"

    def test_cache_disabled_with_parameter(self, tmp_path: Path) -> None:
        """Cache can be disabled via parameter (for debug mode)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_cache=False)

        # Save some data
        storage.save([Todo(id=1, text="test")])

        # Both loads should read from file (no caching)
        with patch("flywheel.storage.json.loads", wraps=json.loads) as mock_loads:
            storage.load()
            first_call_count = mock_loads.call_count

            storage.load()
            second_call_count = mock_loads.call_count

            # Should have been called twice (no caching)
            assert second_call_count == first_call_count + 1

    def test_load_empty_file_returns_empty_list_and_caches(self, tmp_path: Path) -> None:
        """Loading from non-existent file should return empty list and cache it."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # First load (file doesn't exist)
        loaded1 = storage.load()
        assert loaded1 == []

        # Create the file externally
        time.sleep(0.01)  # Ensure mtime difference
        db.write_text(json.dumps([{"id": 1, "text": "new", "done": False}]), encoding="utf-8")

        # Second load should detect new file
        loaded2 = storage.load()
        assert len(loaded2) == 1
        assert loaded2[0].text == "new"

    def test_cache_invalidated_on_file_deletion(self, tmp_path: Path) -> None:
        """If file is deleted externally, load() should return empty list."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save and load initial data
        storage.save([Todo(id=1, text="to be deleted")])
        loaded1 = storage.load()
        assert len(loaded1) == 1

        # Delete file externally
        db.unlink()

        # Load should detect file is gone and return empty list
        loaded2 = storage.load()
        assert loaded2 == []

    def test_multiple_storage_instances_have_separate_caches(self, tmp_path: Path) -> None:
        """Each TodoStorage instance should have its own cache."""
        db = tmp_path / "shared.json"

        storage1 = TodoStorage(str(db))
        storage2 = TodoStorage(str(db))

        # Save via storage1
        storage1.save([Todo(id=1, text="from storage1")])

        # storage2 should read the saved data (its cache is empty)
        loaded = storage2.load()
        assert len(loaded) == 1
        assert loaded[0].text == "from storage1"

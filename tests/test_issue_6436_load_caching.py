"""Regression test for issue #6436: load() should cache file reads.

The load() method should use mtime-based caching to avoid re-reading
the file when it hasn't changed. This improves performance for
applications that call load() frequently.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestLoadCaching:
    """Tests for mtime-based caching in load()."""

    def test_load_caches_when_file_unchanged(self, tmp_path: Path) -> None:
        """Test that load() uses cache when file hasn't changed (same mtime)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # First load reads from file
        result1 = storage.load()
        assert len(result1) == 1

        # Patch the file read to track calls - should not be called on second load
        # since file hasn't changed
        original_read_text = Path.read_text
        read_calls = []

        def tracking_read_text(self, *args, **kwargs):
            read_calls.append(self)
            return original_read_text(self, *args, **kwargs)

        with patch.object(Path, "read_text", tracking_read_text):
            result2 = storage.load()

        # Should return same data without reading file again
        assert len(result2) == 1
        assert result2[0].text == "test todo"
        assert len(read_calls) == 0, "load() should not read file when cache is valid"

    def test_load_reloads_when_file_changes(self, tmp_path: Path) -> None:
        """Test that load() reloads from file when mtime changes."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        todos = [Todo(id=1, text="original")]
        storage.save(todos)

        # First load populates cache
        result1 = storage.load()
        assert result1[0].text == "original"

        # Manually modify file (simulate external change)
        time.sleep(0.01)  # Ensure mtime changes
        db.write_text('[{"id": 2, "text": "modified externally", "done": false, "created_at": "", "updated_at": ""}]')

        # Second load should detect file change and reload
        result2 = storage.load()
        assert result2[0].text == "modified externally"

    def test_load_cache_invalidated_by_save(self, tmp_path: Path) -> None:
        """Test that save() invalidates the cache, so next load reads fresh data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Load to populate cache
        result1 = storage.load()
        assert result1[0].text == "initial"

        # Save new data - should invalidate cache
        new_todos = [Todo(id=1, text="updated via save")]
        storage.save(new_todos)

        # Next load should read from file (cache was invalidated)
        result2 = storage.load()
        assert result2[0].text == "updated via save"

    def test_load_returns_empty_list_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that load() handles non-existent files correctly with caching."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # First load for non-existent file should return empty list
        result1 = storage.load()
        assert result1 == []

        # Second load should also return empty list (cached)
        result2 = storage.load()
        assert result2 == []

        # Create file and load again - should read the new file
        todos = [Todo(id=1, text="newly created")]
        storage.save(todos)

        result3 = storage.load()
        assert len(result3) == 1
        assert result3[0].text == "newly created"

    def test_multiple_storages_have_independent_caches(self, tmp_path: Path) -> None:
        """Test that different storage instances have independent caches."""
        db1 = tmp_path / "todo1.json"
        db2 = tmp_path / "todo2.json"

        storage1 = TodoStorage(str(db1))
        storage2 = TodoStorage(str(db2))

        # Create different data in each
        storage1.save([Todo(id=1, text="storage1 todo")])
        storage2.save([Todo(id=2, text="storage2 todo")])

        # Load from both
        result1 = storage1.load()
        result2 = storage2.load()

        assert result1[0].text == "storage1 todo"
        assert result2[0].text == "storage2 todo"

        # Modify storage1's file
        storage1.save([Todo(id=1, text="storage1 updated")])

        # storage2's cache should still be valid
        result2_again = storage2.load()
        assert result2_again[0].text == "storage2 todo"

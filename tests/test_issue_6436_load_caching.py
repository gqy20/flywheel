"""Tests for load() caching mechanism (issue #6436).

This test suite verifies that TodoStorage.load() implements an mtime-based
cache to avoid reading the file on every call when the file hasn't changed.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_uses_cache_when_file_unchanged(tmp_path: Path) -> None:
    """Test that load() uses cache and doesn't re-read file when mtime unchanged."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # First load should read the file
    loaded1 = storage.load()
    assert len(loaded1) == 1
    assert loaded1[0].text == "initial"

    # Track how many times the file is actually read
    original_read_text = Path.read_text
    read_count = [0]

    def counting_read_text(self, *args, **kwargs):
        read_count[0] += 1
        return original_read_text(self, *args, **kwargs)

    # Patch Path.read_text to count file reads
    with patch.object(Path, "read_text", counting_read_text):
        # Second load should use cache (no file read)
        loaded2 = storage.load()
        assert len(loaded2) == 1
        assert loaded2[0].text == "initial"
        # Should have read the file 0 times (cache hit)
        assert read_count[0] == 0, "load() should use cache when file unchanged"


def test_cache_invalidated_on_file_modification(tmp_path: Path) -> None:
    """Test that cache is invalidated when file is modified externally."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Load to populate cache
    loaded1 = storage.load()
    assert len(loaded1) == 1
    assert loaded1[0].text == "initial"

    # Modify file externally (simulating another process)
    # Need to wait a bit to ensure mtime changes (filesystem mtime granularity)
    time.sleep(0.01)
    external_todos = [Todo(id=1, text="external"), Todo(id=2, text="added")]
    storage2 = TodoStorage(str(db))
    storage2.save(external_todos)

    # Next load should detect mtime change and re-read
    loaded2 = storage.load()
    assert len(loaded2) == 2
    assert loaded2[0].text == "external"
    assert loaded2[1].text == "added"


def test_save_updates_cache(tmp_path: Path) -> None:
    """Test that save() updates the cache with saved data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Load to populate cache
    loaded1 = storage.load()
    assert len(loaded1) == 1

    # Save new data (should update cache with new data)
    new_todos = [Todo(id=1, text="updated"), Todo(id=2, text="new")]
    storage.save(new_todos)

    # Track file reads after save
    original_read_text = Path.read_text
    read_count = [0]

    def counting_read_text(self, *args, **kwargs):
        read_count[0] += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", counting_read_text):
        # Load after save should NOT read file (cache was updated by save)
        loaded2 = storage.load()
        assert len(loaded2) == 2
        assert loaded2[0].text == "updated"
        # Should have read the file 0 times (cache was updated by save)
        assert read_count[0] == 0, "load() should use updated cache after save"


def test_cache_returns_same_objects_when_unchanged(tmp_path: Path) -> None:
    """Test that cached loads return the same todo objects when file unchanged."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Load twice
    loaded1 = storage.load()
    loaded2 = storage.load()

    # Should be equal (same content)
    assert len(loaded1) == len(loaded2) == 1
    assert loaded1[0].id == loaded2[0].id
    assert loaded1[0].text == loaded2[0].text


def test_nonexistent_file_returns_empty_list_consistently(tmp_path: Path) -> None:
    """Test that load() on nonexistent file returns empty list without caching error."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # First load on nonexistent file
    loaded1 = storage.load()
    assert loaded1 == []

    # Second load should still work (and use cache)
    loaded2 = storage.load()
    assert loaded2 == []

    # Now create the file
    todos = [Todo(id=1, text="newly created")]
    storage.save(todos)

    # Load should now return the actual data
    loaded3 = storage.load()
    assert len(loaded3) == 1
    assert loaded3[0].text == "newly created"


def test_performance_multiple_loads_without_save(tmp_path: Path) -> None:
    """Performance test: multiple loads without save should not re-read file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create data with many todos
    todos = [Todo(id=i, text=f"todo-{i}") for i in range(100)]
    storage.save(todos)

    # Track file reads
    original_read_text = Path.read_text
    read_count = [0]

    def counting_read_text(self, *args, **kwargs):
        read_count[0] += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", counting_read_text):
        # Perform 100 loads
        for _ in range(100):
            loaded = storage.load()
            assert len(loaded) == 100

        # Should have read the file 0 times (all cache hits)
        # First load after save will miss cache, but subsequent loads should hit
        assert read_count[0] == 0, "Multiple loads should use cache, not re-read file"

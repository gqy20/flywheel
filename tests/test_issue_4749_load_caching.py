"""Tests for load() caching mechanism (Issue #4749).

This test suite verifies that TodoStorage.load() caches data based on
file modification time, avoiding repeated disk I/O for unchanged files.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_uses_cache_when_file_unchanged(tmp_path: Path) -> None:
    """Test that load() returns cached data when file mtime unchanged.

    This test verifies that repeated load() calls avoid file I/O by using
    an in-memory cache that's invalidated when the file's mtime changes.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="cached")]
    storage.save(todos)

    # First load - should read from file and cache it
    first_load = storage.load()

    # Second load - should return the SAME list object from cache
    # (not just equal data, but the same object reference)
    second_load = storage.load()

    # Verify that the cache is being used - same object reference
    assert second_load is first_load, (
        "load() should return cached list object when file unchanged"
    )

    # Data should be identical
    assert len(second_load) == 1
    assert second_load[0].text == "cached"


def test_load_invalidates_cache_when_file_modified(tmp_path: Path) -> None:
    """Test that load() re-reads file when mtime changes."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    storage.save([Todo(id=1, text="original")])
    first_load = storage.load()
    assert first_load[0].text == "original"

    # Modify file externally (simulate another process)
    time.sleep(0.01)  # Ensure mtime changes
    storage.save([Todo(id=1, text="modified"), Todo(id=2, text="new")])

    # Load should detect file change and re-read
    second_load = storage.load()
    assert len(second_load) == 2
    assert second_load[0].text == "modified"
    assert second_load[1].text == "new"


def test_load_cache_respects_different_files(tmp_path: Path) -> None:
    """Test that each storage instance has its own cache."""
    db1 = tmp_path / "todo1.json"
    db2 = tmp_path / "todo2.json"

    storage1 = TodoStorage(str(db1))
    storage2 = TodoStorage(str(db2))

    storage1.save([Todo(id=1, text="one")])
    storage2.save([Todo(id=1, text="two")])

    # Each storage should return its own data
    loaded1 = storage1.load()
    loaded2 = storage2.load()

    assert loaded1[0].text == "one"
    assert loaded2[0].text == "two"


def test_load_returns_empty_list_for_nonexistent_file(tmp_path: Path) -> None:
    """Test that load() returns [] for non-existent file and caches it."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # First call
    result1 = storage.load()
    assert result1 == []

    # Second call should return the SAME empty list from cache
    result2 = storage.load()
    assert result2 is result1, "Should return cached empty list"


def test_cache_cleared_on_save(tmp_path: Path) -> None:
    """Test that save() invalidates the cache so next load reads fresh data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save and load initial data
    storage.save([Todo(id=1, text="initial")])
    first_load = storage.load()
    assert first_load[0].text == "initial"

    # Save new data (should invalidate cache)
    storage.save([Todo(id=1, text="updated")])

    # Load should return new data
    second_load = storage.load()
    assert second_load[0].text == "updated"


def test_performance_multiple_loads_unchanged_file(tmp_path: Path) -> None:
    """Performance test: multiple loads of unchanged file should be fast."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create some data
    storage.save([Todo(id=i, text=f"task-{i}") for i in range(10)])

    # Warm up cache
    storage.load()

    # Measure time for cached loads
    start = time.perf_counter()
    for _ in range(1000):
        storage.load()
    cached_time = time.perf_counter() - start

    # Should be fast (< 100ms for 1000 cached loads)
    assert cached_time < 0.1, f"Cached loads took {cached_time:.3f}s, expected < 0.1s"

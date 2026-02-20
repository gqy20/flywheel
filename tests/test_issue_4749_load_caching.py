"""Tests for load() caching mechanism in TodoStorage.

This test suite verifies that TodoStorage.load() implements caching
to avoid redundant file I/O on repeated calls when the file hasn't changed.

Issue: #4749
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_caches_result_when_file_unchanged(tmp_path: Path) -> None:
    """Test that repeated load() calls use cached data when file hasn't changed."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save initial todos
    todos = [Todo(id=1, text="cached task")]
    storage.save(todos)

    # First load - should read from file and populate cache
    storage.load()

    # Patch read_text to detect if file is read again
    original_read_text = Path.read_text
    read_count = [0]

    def tracked_read_text(self, *args, **kwargs):
        if self == db:
            read_count[0] += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", tracked_read_text):
        # Second load - should use cache (no file read)
        result2 = storage.load()

    # Should have returned the same data
    assert len(result2) == 1
    assert result2[0].text == "cached task"

    # File should NOT have been read again (cache hit)
    assert read_count[0] == 0, f"Expected 0 file reads for cached load, got {read_count[0]}"


def test_load_invalidates_cache_after_save(tmp_path: Path) -> None:
    """Test that cache is invalidated after save() is called."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save initial data
    storage.save([Todo(id=1, text="initial")])

    # Load once to populate cache
    result1 = storage.load()
    assert len(result1) == 1
    assert result1[0].text == "initial"

    # Save new data (should invalidate cache)
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])

    # Load again - should read fresh data
    result2 = storage.load()
    assert len(result2) == 2
    assert result2[0].text == "updated"
    assert result2[1].text == "new"


def test_load_invalidates_cache_when_file_modified_externally(tmp_path: Path) -> None:
    """Test that cache is invalidated when file is modified externally.

    Uses file modification time (mtime) to detect external changes.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save initial data
    storage.save([Todo(id=1, text="initial")])

    # Load once to populate cache
    result1 = storage.load()
    assert result1[0].text == "initial"

    # Simulate external modification by updating file directly
    # and ensuring mtime changes
    time.sleep(0.01)  # Ensure mtime is different
    db.write_text('[{"id": 1, "text": "externally modified", "done": false}]', encoding="utf-8")

    # Load again - should detect external change and reload
    result2 = storage.load()
    assert result2[0].text == "externally modified"


def test_load_performance_improvement_with_caching(tmp_path: Path) -> None:
    """Test that caching provides measurable performance improvement."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a reasonably sized dataset
    num_todos = 100
    todos = [Todo(id=i, text=f"task {i}" * 10) for i in range(1, num_todos + 1)]
    storage.save(todos)

    # Measure time for multiple loads (with caching)
    start_cached = time.perf_counter()
    for _ in range(100):
        storage.load()
    cached_time = time.perf_counter() - start_cached

    # Measure time for loads without cache benefit (fresh instances)
    start_no_cache = time.perf_counter()
    for _ in range(100):
        TodoStorage(str(db)).load()  # Fresh instance each time
    no_cache_time = time.perf_counter() - start_no_cache

    # Cached version should be significantly faster
    # (At least 2x improvement is a reasonable expectation)
    improvement_ratio = no_cache_time / cached_time
    assert improvement_ratio >= 2, (
        f"Expected at least 2x improvement with caching, got {improvement_ratio:.1f}x "
        f"(cached: {cached_time:.4f}s, no_cache: {no_cache_time:.4f}s)"
    )


def test_load_returns_copy_of_cached_data(tmp_path: Path) -> None:
    """Test that cached data is returned as a copy to prevent mutation issues."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="original")])

    # Get first load
    result1 = storage.load()

    # Mutate the result
    result1[0].text = "mutated"

    # Get second load - should still have original data
    result2 = storage.load()
    assert result2[0].text == "original", "Cache should not be affected by mutation of returned data"


def test_load_empty_file_caching(tmp_path: Path) -> None:
    """Test that empty file result is also cached properly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No file exists - should return empty list
    result1 = storage.load()
    assert result1 == []

    # Track file reads
    original_exists = Path.exists
    exists_calls = [0]

    def tracked_exists(self):
        if self == db:
            exists_calls[0] += 1
        return original_exists(self)

    with patch.object(Path, "exists", tracked_exists):
        result2 = storage.load()

    # Should still return empty list
    assert result2 == []

    # File existence check should have been called (for mtime check or cache validation)
    # But the key is that we don't repeatedly check if the file doesn't exist

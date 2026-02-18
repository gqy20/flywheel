"""Tests for caching behavior in TodoStorage.load().

This test suite verifies that TodoStorage.load() caches the "file not found"
result to avoid repeated file system checks when the database file doesn't exist.

Issue #4341: load method does not cache result when file doesn't exist,
causing repeated file existence checks on frequent calls.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage


def test_load_caches_file_not_found_result(tmp_path: Path) -> None:
    """Test that load() caches the result when file doesn't exist.

    When the file doesn't exist, subsequent load() calls should not
    repeatedly check file existence, improving performance for high-frequency
    read scenarios.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track how many times Path.exists() is called
    exists_call_count = 0
    original_exists = Path.exists

    def tracking_exists(self):
        nonlocal exists_call_count
        if self == db:
            exists_call_count += 1
        return original_exists(self)

    with patch.object(Path, "exists", tracking_exists):
        # First call - file doesn't exist, should call exists()
        result1 = storage.load()
        assert result1 == []
        first_exists_count = exists_call_count
        assert first_exists_count >= 1, "Should check file existence on first load"

        # Second call - should use cached result, not call exists() again
        result2 = storage.load()
        assert result2 == []
        second_exists_count = exists_call_count

        # The key assertion: exists() should not be called again
        # because the "file not found" result was cached
        assert second_exists_count == first_exists_count, (
            f"File existence should be cached after first call. "
            f"First: {first_exists_count}, Second: {second_exists_count}"
        )


def test_load_cache_invalidated_after_save(tmp_path: Path) -> None:
    """Test that the cache is invalidated after a save operation.

    After saving data, the next load() should check the file again
    and return the saved data.
    """
    from flywheel.todo import Todo

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First load - file doesn't exist, cached as empty
    result1 = storage.load()
    assert result1 == []

    # Save some data - this should invalidate the cache
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Second load - should read from file now
    result2 = storage.load()
    assert len(result2) == 1
    assert result2[0].text == "test todo"


def test_load_cache_returns_consistent_results(tmp_path: Path) -> None:
    """Test that cached results are consistent across multiple calls."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Multiple loads should return consistent results
    for _ in range(10):
        result = storage.load()
        assert result == [], "Should consistently return empty list for non-existent file"

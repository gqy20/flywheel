"""Tests for Issue #4625: Redundant I/O in load method.

This test verifies that the load method does not make redundant stat calls:
- load should use single stat call when file exists
- load should handle FileNotFoundError gracefully when file doesn't exist
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_load_single_stat_call_when_file_exists(tmp_path) -> None:
    """Issue #4625: load should only call stat() once when file exists."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Track how many times Path.stat is called
    stat_call_count = 0
    original_stat = Path.stat

    def counting_stat(self, *, follow_symlinks=True):
        nonlocal stat_call_count
        stat_call_count += 1
        return original_stat(self, follow_symlinks=follow_symlinks)

    with patch.object(Path, "stat", counting_stat):
        # Load should only call stat once
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

        # Verify only one stat call was made
        # Previous implementation: exists() calls stat once, then stat() calls again = 2 calls
        # Fixed implementation: single try/except stat call = 1 call
        assert stat_call_count == 1, (
            f"Expected 1 stat call, got {stat_call_count}. "
            "load() should consolidate exists() and stat() into single stat call."
        )


def test_storage_load_returns_empty_list_when_file_not_exists(tmp_path) -> None:
    """Issue #4625: load should return [] gracefully when file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist - should return empty list without exception
    loaded = storage.load()
    assert loaded == []


def test_storage_load_single_stat_call_when_file_not_exists(tmp_path) -> None:
    """Issue #4625: load should use single stat (via try/except) for non-existent file."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Track how many times Path.stat is called
    stat_call_count = 0
    original_stat = Path.stat

    def counting_stat(self, *, follow_symlinks=True):
        nonlocal stat_call_count
        stat_call_count += 1
        return original_stat(self, follow_symlinks=follow_symlinks)

    with patch.object(Path, "stat", counting_stat):
        # Load should only attempt stat once
        loaded = storage.load()
        assert loaded == []

        # Verify only one stat call was made (which raised FileNotFoundError)
        # Previous: exists() calls stat once (returns False), never calls stat() again
        # This test ensures we don't regress to calling stat multiple times
        assert stat_call_count == 1, (
            f"Expected 1 stat call attempt, got {stat_call_count}. "
            "load() should use single try/except stat call for non-existent file."
        )


def test_storage_load_file_size_check_still_works(tmp_path) -> None:
    """Verify that after the fix, size validation still works correctly."""
    db = tmp_path / "normal.json"
    storage = TodoStorage(str(db))

    # Create a normal-sized JSON file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"

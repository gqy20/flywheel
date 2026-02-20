"""Tests for issue #4625: load method should use single stat() call.

This test suite verifies that the load() method in TodoStorage minimizes
redundant I/O operations by using a single stat() system call instead of
calling both exists() and stat() separately.

Issue: https://github.com/gqy20/flywheel/issues/4625
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_uses_single_stat_call_when_file_exists(tmp_path) -> None:
    """Verify load() only calls stat once when file exists.

    Previously, load() would call path.exists() (which internally uses stat)
    and then path.stat() again, resulting in two system calls for the same
    information.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Track stat() calls
    stat_call_count = 0
    original_stat = Path.stat

    def counting_stat(self, *args, **kwargs):
        nonlocal stat_call_count
        stat_call_count += 1
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", counting_stat):
        loaded = storage.load()

    # Should only call stat once for the entire load operation
    assert stat_call_count == 1, (
        f"Expected 1 stat() call, got {stat_call_count}. "
        "load() should use single stat call via try/except pattern."
    )
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_load_returns_empty_list_when_file_not_exists(tmp_path) -> None:
    """Verify load() returns [] when file doesn't exist without errors."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist - should return empty list
    result = storage.load()
    assert result == []


def test_load_single_stat_with_nonexistent_file(tmp_path) -> None:
    """Verify load() uses single stat attempt when file doesn't exist.

    When file doesn't exist, load() should catch FileNotFoundError
    from stat() and return [], rather than calling exists() first.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Track stat() calls
    stat_call_count = 0
    original_stat = Path.stat

    def counting_stat(self, *args, **kwargs):
        nonlocal stat_call_count
        stat_call_count += 1
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", counting_stat):
        result = storage.load()

    # Should only call stat once (which raises FileNotFoundError)
    assert stat_call_count == 1, (
        f"Expected 1 stat() call for nonexistent file, got {stat_call_count}"
    )
    assert result == []


def test_load_preserves_size_validation(tmp_path) -> None:
    """Verify size validation still works after optimization."""
    import json

    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a JSON file larger than 10MB (~11MB)
    large_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100}
        for i in range(75000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Verify the file is actually larger than 10MB
    assert db.stat().st_size > 10 * 1024 * 1024, (
        f"Test file too small: {db.stat().st_size} bytes"
    )

    # Should raise ValueError for oversized file
    with pytest.raises(ValueError, match="too large"):
        storage.load()

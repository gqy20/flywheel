"""Regression test for issue #2565: TOCTOU race condition in load().

This test verifies that load() handles the race condition between exists()
check and stat() call gracefully by catching FileNotFoundError directly.

The bug was:
1. exists() returns True
2. File is deleted by another process
3. stat() raises FileNotFoundError (unhandled)

The fix combines the operations by catching the FileNotFoundError from stat()
directly, eliminating the race window.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage


def test_load_handles_file_deleted_between_exists_and_stat(tmp_path) -> None:
    """Test that load() handles file deleted between exists() and stat().

    This simulates the TOCTOU race condition where:
    1. exists() returns True (file exists)
    2. File is deleted by another process
    3. stat() raises FileNotFoundError

    The fixed code should catch this and return [] gracefully.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    db.write_text("[]", encoding="utf-8")

    # Track call count to delete file on second call (during stat)
    call_count = 0

    def stat_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # On first call (exists check), return True normally
        if call_count == 1:
            return db.stat()  # Normal stat for exists()
        # On second call (file_size check), simulate file deletion
        raise FileNotFoundError(f"[Errno 2] No such file or directory: '{db}'")

    original_stat = Path.stat

    with patch.object(Path, "stat", side_effect=stat_side_effect):
        # load() should handle FileNotFoundError and return []
        result = storage.load()
        assert result == []

    # Verify normal case still works
    Path.stat = original_stat
    result = storage.load()
    assert result == []


def test_load_returns_empty_list_when_file_does_not_exist(tmp_path) -> None:
    """Test that load() returns [] when file doesn't exist (happy path)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []


def test_load_works_correctly_when_file_exists(tmp_path) -> None:
    """Test that load() works correctly when file exists (happy path)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create valid data
    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")

    result = storage.load()
    assert len(result) == 1
    assert result[0].text == "test"


def test_load_respects_max_file_size_limit(tmp_path) -> None:
    """Test that load() still enforces file size limit after fix."""
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a file larger than the limit
    large_content = "x" * (11 * 1024 * 1024)  # 11MB
    db.write_text(large_content, encoding="utf-8")

    with pytest.raises(ValueError, match="JSON file too large"):
        storage.load()

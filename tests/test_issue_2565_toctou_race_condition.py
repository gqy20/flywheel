"""Regression tests for issue #2565: TOCTOU race condition in load().

Issue: The load() method has a Time-of-Check-Time-of-Use (TOCTOU) race condition:
1. Line 60: self.path.exists() check
2. Line 64: self.path.stat() call

Between these two operations, an attacker could:
1. File exists at check time
2. Attacker deletes file after check passes
3. stat() call raises FileNotFoundError (unexpected error)

The fix is to remove the exists() check and handle FileNotFoundError directly
from the stat() call, using the "ask forgiveness, not permission" pattern.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_returns_empty_list_when_file_does_not_exist(tmp_path) -> None:
    """Issue #2565: load() should return [] when file doesn't exist.

    This tests the happy path - file doesn't exist, should return empty list.
    This test should PASS both before and after the fix.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist, should return empty list
    loaded = storage.load()
    assert loaded == []


def test_load_handles_missing_file_after_exists_check(tmp_path) -> None:
    """Issue #2565: load() should handle file deletion between exists() and stat().

    This simulates the TOCTOU race condition where:
    1. exists() returns True (file exists)
    2. Attacker deletes the file
    3. stat() raises FileNotFoundError

    Before fix: This would raise an unhandled FileNotFoundError
    After fix: Should return [] gracefully

    We mock exists() to return True, then make stat() raise FileNotFoundError.
    """
    db = tmp_path / "race_condition.json"
    storage = TodoStorage(str(db))

    # Mock exists() to return True (file exists at check time)
    # But stat() raises FileNotFoundError (file deleted before use)
    with (
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "stat", side_effect=FileNotFoundError("Simulated race condition")),
    ):
        # Should return [] gracefully, not raise FileNotFoundError
        loaded = storage.load()
        assert loaded == []


def test_load_works_correctly_when_file_exists(tmp_path) -> None:
    """Issue #2565: load() should work normally when file exists.

    This tests the normal case - file exists and has valid content.
    This test should PASS both before and after the fix.
    """
    db = tmp_path / "existing.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]
    storage.save(todos)

    # Load should work correctly
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True


def test_load_respects_max_file_size(tmp_path) -> None:
    """Issue #2565: File size check should still work after TOCTOU fix.

    The fix shouldn't break the existing DoS protection via file size limit.
    """
    db = tmp_path / "large_file.json"
    storage = TodoStorage(str(db))

    # Create a file larger than the limit (10MB)
    large_content = "[" + ",".join(['{"id":1,"text":"x"}' for _ in range(1000000)]) + "]"
    db.write_text(large_content)

    # Should raise ValueError for file too large
    try:
        storage.load()
        raise AssertionError("Should have raised ValueError for large file")
    except ValueError as e:
        assert "too large" in str(e).lower()


def test_load_handles_invalid_json_after_race_condition(tmp_path) -> None:
    """Issue #2565: Invalid JSON handling should still work after TOCTOU fix.

    Even if file exists, if it has invalid JSON, should raise ValueError.
    """
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Create file with invalid JSON
    db.write_text("{invalid json}")

    # Should raise ValueError for invalid JSON
    try:
        storage.load()
        raise AssertionError("Should have raised ValueError for invalid JSON")
    except ValueError as e:
        assert "invalid json" in str(e).lower()

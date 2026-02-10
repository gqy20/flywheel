"""Regression test for issue #2565: TOCTOU race condition in load().

This test suite verifies that TodoStorage.load() handles the race condition
between exists() check and stat() call gracefully, without crashing.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_returns_empty_list_when_file_does_not_exist(tmp_path) -> None:
    """Test that load() returns [] when file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist, should return empty list
    loaded = storage.load()
    assert loaded == []


def test_load_handles_file_deleted_between_exists_and_stat(tmp_path) -> None:
    """Regression test for issue #2565: TOCTOU race condition.

    Tests that load() handles the case where a file is deleted between
    the exists() check and stat() call. The fix uses try-except around
    stat() instead of check-then-act pattern.
    """
    db = tmp_path / "race_condition.json"
    storage = TodoStorage(str(db))

    # First, create a file so exists() returns True initially
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Mock Path.exists to return True (simulating file exists at check time)
    # But make stat() raise FileNotFoundError (simulating file deleted before stat)
    original_exists = Path.exists
    original_stat = Path.stat

    def mock_exists(self):
        # For our test file, return True to pass the exists() check
        if self == db:
            return True
        return original_exists(self)

    def mock_stat(self):
        # For our test file, raise FileNotFoundError to simulate deletion
        if self == db:
            raise FileNotFoundError(f"[Errno 2] No such file or directory: '{self}'")
        return original_stat(self)

    with (
        patch.object(Path, "exists", mock_exists),
        patch.object(Path, "stat", mock_stat),
    ):
        # Should return [] instead of crashing
        loaded = storage.load()
        assert loaded == []

    # Verify normal operation still works when file exists
    loaded = storage.load()  # This uses real file operations
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_load_works_correctly_when_file_exists(tmp_path) -> None:
    """Test that load() works correctly when file exists and is valid."""
    db = tmp_path / "exists.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second", done=True),
    ]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first"
    assert loaded[0].done is False
    assert loaded[1].text == "second"
    assert loaded[1].done is True

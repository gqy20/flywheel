"""Regression test for issue #4131: TOCTOU race condition in load().

This test verifies that load() handles FileNotFoundError gracefully when
a file is deleted between the exists() check and the stat() call.
"""

from __future__ import annotations

import os
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_handles_file_deleted_between_exists_and_stat(tmp_path) -> None:
    """Regression test for issue #4131: TOCTOU race condition.

    Uses a mock to simulate the race condition where exists() returns True
    but stat() raises FileNotFoundError.
    """
    db = tmp_path / "race.json"
    storage = TodoStorage(str(db))

    # Create a valid file first
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Create a mock path that simulates TOCTOU:
    # - exists() returns True
    # - stat() raises FileNotFoundError
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.stat.side_effect = FileNotFoundError(
        "File deleted between exists() and stat()"
    )

    # Replace storage.path with mock
    with patch.object(storage, "path", mock_path):
        # load() should handle FileNotFoundError gracefully and return []
        result = storage.load()
        assert result == [], "load() should return [] when file disappears"


def test_load_handles_stat_file_not_found_directly(tmp_path) -> None:
    """Test that load() handles FileNotFoundError from stat() directly.

    Uses a mock to simulate stat() raising FileNotFoundError.
    """
    db = tmp_path / "missing.json"
    storage = TodoStorage(str(db))

    # Create a mock path that simulates file not existing (stat raises FileNotFoundError)
    mock_path = MagicMock()
    mock_path.stat.side_effect = FileNotFoundError(f"No such file: {db}")

    # Replace storage.path with mock
    with patch.object(storage, "path", mock_path):
        # load() should catch FileNotFoundError and return []
        result = storage.load()
        assert result == []


def test_load_race_condition_real_file_deletion(tmp_path) -> None:
    """Integration test: delete file during load() to simulate real TOCTOU race.

    This test uses a background thread to delete the file immediately after
    load() starts, simulating a real race condition.
    """
    db = tmp_path / "race_real.json"
    storage = TodoStorage(str(db))

    # Create a valid file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    deleted = False

    def delete_file_soon():
        """Delete file after a short delay."""
        nonlocal deleted
        time.sleep(0.001)  # Small delay to let load() start
        try:
            os.unlink(db)
            deleted = True
        except FileNotFoundError:
            pass  # File already deleted

    # Start thread that will delete file during load
    deleter = threading.Thread(target=delete_file_soon)
    deleter.start()

    try:
        # load() should handle race condition gracefully
        result = storage.load()
        # Either the file was deleted before we read it (return []) or
        # we successfully read the data (return [Todo(...)])
        assert isinstance(result, list)
    except FileNotFoundError:
        # This is the bug - should not raise FileNotFoundError
        pytest.fail("load() raised FileNotFoundError - TOCTOU bug exists!")
    finally:
        deleter.join(timeout=1)


def test_load_returns_empty_for_nonexistent_file(tmp_path) -> None:
    """Baseline test: load() returns [] for a file that doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Verify the file doesn't exist
    assert not db.exists()

    # load() should return empty list without raising
    result = storage.load()
    assert result == []


def test_load_still_works_with_existing_file(tmp_path) -> None:
    """Baseline test: load() still works normally with existing files."""
    db = tmp_path / "existing.json"
    storage = TodoStorage(str(db))

    # Create a valid file
    original_todos = [Todo(id=1, text="task"), Todo(id=2, text="another")]
    storage.save(original_todos)

    # load() should return the saved todos
    result = storage.load()
    assert len(result) == 2
    assert result[0].text == "task"
    assert result[1].text == "another"

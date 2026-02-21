"""Tests for TodoStorage.exists() method.

This test suite verifies the existence check functionality added in issue #4932.
The exists() method provides an efficient way to check if the database file exists
without loading it or parsing JSON.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_before_save(tmp_path: Path) -> None:
    """Test that exists() returns False when the database file does not exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path: Path) -> None:
    """Test that exists() returns True after saving todos."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initially should not exist
    assert storage.exists() is False

    # Save some todos
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Now should exist
    assert storage.exists() is True


def test_exists_does_not_raise_on_missing_file(tmp_path: Path) -> None:
    """Test that exists() does not raise an exception when file is missing."""
    db = tmp_path / "nonexistent" / "todo.json"
    storage = TodoStorage(str(db))

    # Should not raise, just return False
    assert storage.exists() is False


def test_exists_does_not_read_file_contents(tmp_path: Path) -> None:
    """Test that exists() returns True even if file has invalid JSON.

    This verifies that exists() only checks file existence, not content validity.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write invalid JSON directly to the file
    db.write_text("not valid json {", encoding="utf-8")

    # exists() should return True (file exists)
    assert storage.exists() is True

    # load() would fail with invalid JSON
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()


def test_exists_with_custom_path(tmp_path: Path) -> None:
    """Test that exists() works correctly with a custom database path."""
    db = tmp_path / "subdir" / "custom.json"
    storage = TodoStorage(str(db))

    # Should not exist initially
    assert storage.exists() is False

    # Save creates the file (and parent directory)
    storage.save([Todo(id=1, text="custom path todo")])

    # Now should exist
    assert storage.exists() is True


def test_exists_returns_false_after_file_deleted(tmp_path: Path) -> None:
    """Test that exists() returns False after the file is deleted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save
    storage.save([Todo(id=1, text="temporary")])
    assert storage.exists() is True

    # Delete the file
    db.unlink()

    # Should now return False
    assert storage.exists() is False

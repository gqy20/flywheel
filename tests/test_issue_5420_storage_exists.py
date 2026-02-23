"""Tests for issue #5420: TodoStorage.exists() method.

This test suite verifies that TodoStorage.exists() correctly reports
whether the storage file exists.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_when_file_does_not_exist(tmp_path) -> None:
    """Test that exists() returns False when storage file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path) -> None:
    """Test that exists() returns True after save() is called."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # File should not exist initially
    assert storage.exists() is False

    # Save some todos
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Now exists() should return True
    assert storage.exists() is True


def test_exists_returns_bool_type(tmp_path) -> None:
    """Test that exists() returns a bool type."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    result = storage.exists()
    assert isinstance(result, bool)


def test_exists_returns_false_after_manual_delete(tmp_path) -> None:
    """Test that exists() reflects file state after manual deletion."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save and verify exists
    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    assert storage.exists() is True

    # Manually delete file
    Path(str(db)).unlink()

    # exists() should now return False
    assert storage.exists() is False

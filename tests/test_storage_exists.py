"""Tests for TodoStorage.exists() method.

This test suite verifies that TodoStorage.exists() correctly checks
whether the storage file exists, providing a consistent API for callers.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_when_file_does_not_exist(tmp_path) -> None:
    """Test that exists() returns False when storage file does not exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # File does not exist yet
    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path) -> None:
    """Test that exists() returns True after save() is called."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initially doesn't exist
    assert storage.exists() is False

    # After save, it should exist
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert storage.exists() is True


def test_exists_return_type_is_bool(tmp_path) -> None:
    """Test that exists() returns a bool type."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    result = storage.exists()

    assert isinstance(result, bool)


def test_exists_with_explicit_path(tmp_path) -> None:
    """Test that exists() works with different storage paths."""
    db1 = tmp_path / "storage1.json"
    db2 = tmp_path / "storage2.json"

    storage1 = TodoStorage(str(db1))
    storage2 = TodoStorage(str(db2))

    # Neither exists initially
    assert storage1.exists() is False
    assert storage2.exists() is False

    # Save to storage1 only
    storage1.save([Todo(id=1, text="test")])

    # Now storage1 exists but storage2 doesn't
    assert storage1.exists() is True
    assert storage2.exists() is False

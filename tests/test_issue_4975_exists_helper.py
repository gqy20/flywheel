"""Tests for issue #4975: Add file existence check helper method.

This test suite verifies that TodoStorage.exists() correctly reports
whether the database file exists, improving API ergonomics for users
and CLI code.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_before_any_save(tmp_path) -> None:
    """Test that exists() returns False before any save operation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # File does not exist yet
    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path) -> None:
    """Test that exists() returns True after save operation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save creates the file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # File should now exist
    assert storage.exists() is True


def test_exists_returns_false_after_file_is_deleted(tmp_path) -> None:
    """Test that exists() returns False after file is deleted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save a todo
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)
    assert storage.exists() is True

    # Delete the file manually
    db.unlink()

    # exists() should now return False
    assert storage.exists() is False


def test_exists_returns_true_for_existing_file(tmp_path) -> None:
    """Test that exists() returns True for pre-existing database file."""
    db = tmp_path / "todo.json"

    # Create file manually (simulate pre-existing database)
    db.write_text('[]', encoding="utf-8")

    storage = TodoStorage(str(db))
    assert storage.exists() is True


def test_exists_with_custom_path(tmp_path) -> None:
    """Test that exists() works with custom database paths."""
    custom_db = tmp_path / "custom" / "my_database.json"
    storage = TodoStorage(str(custom_db))

    # Does not exist yet
    assert storage.exists() is False

    # Save creates it
    todos = [Todo(id=1, text="custom path todo")]
    storage.save(todos)

    # Now exists
    assert storage.exists() is True

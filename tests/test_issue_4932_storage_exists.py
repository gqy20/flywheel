"""Tests for TodoStorage.exists() method.

This test suite verifies that TodoStorage.exists() efficiently checks
if the database file exists without loading it.

Issue: #4932
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_before_save(tmp_path) -> None:
    """Test that exists() returns False when database file does not exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # File doesn't exist yet
    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path) -> None:
    """Test that exists() returns True after saving to database."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initially doesn't exist
    assert storage.exists() is False

    # Save some todos
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Now it should exist
    assert storage.exists() is True


def test_exists_does_not_raise_on_missing_file(tmp_path) -> None:
    """Test that exists() does not raise exception on missing file."""
    db = tmp_path / "nonexistent" / "todo.json"
    storage = TodoStorage(str(db))

    # Should not raise, just return False
    assert storage.exists() is False


def test_exists_does_not_load_file_contents(tmp_path, monkeypatch) -> None:
    """Test that exists() does not read file contents or parse JSON."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with invalid JSON
    db.write_text("not valid json", encoding="utf-8")

    # exists() should still return True without attempting to parse
    # If it tried to parse, it would raise ValueError
    assert storage.exists() is True


def test_exists_with_custom_path(tmp_path) -> None:
    """Test that exists() works correctly with custom path."""
    db = tmp_path / "custom" / "database.json"
    storage = TodoStorage(str(db))

    # Initially doesn't exist
    assert storage.exists() is False

    # Save and check again
    storage.save([Todo(id=1, text="test")])
    assert storage.exists() is True

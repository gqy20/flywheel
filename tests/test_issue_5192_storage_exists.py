"""Tests for issue #5192: TodoStorage.exists() method.

This test suite verifies that TodoStorage provides an exists() method
to check if the storage file exists without requiring callers to know
internal path implementation details.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_when_file_not_created(tmp_path) -> None:
    """Test that exists() returns False when storage file doesn't exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path) -> None:
    """Test that exists() returns True after save() creates the file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Before save, file doesn't exist
    assert storage.exists() is False

    # After save, file exists
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert storage.exists() is True


def test_exists_returns_true_for_existing_file(tmp_path) -> None:
    """Test that exists() returns True for pre-existing storage file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file externally
    db.write_text('[]', encoding="utf-8")

    assert storage.exists() is True


def test_exists_returns_false_for_nonexistent_directory(tmp_path) -> None:
    """Test that exists() returns False when path directory doesn't exist."""
    nonexistent = tmp_path / "nonexistent" / "subdir" / "todo.json"
    storage = TodoStorage(str(nonexistent))

    assert storage.exists() is False


def test_exists_with_default_path(tmp_path, monkeypatch) -> None:
    """Test exists() works with default path (.todo.json in cwd)."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    storage = TodoStorage()  # Uses default .todo.json

    # Default path doesn't exist initially
    assert storage.exists() is False

    # Create the file
    Path(".todo.json").write_text('[]', encoding="utf-8")

    assert storage.exists() is True

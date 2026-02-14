"""Regression tests for issue #3362: load() should reject symlinks and non-regular files.

Issue: The load() method only checks path.exists() but doesn't verify that the path
is a regular file. This could allow reading from symlinks that point to sensitive files.

Security Impact: An attacker could create a symlink from the todo database path
to a sensitive file (e.g., /etc/passwd) and read its contents.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_rejects_symlink_to_regular_file(tmp_path) -> None:
    """Issue #3362: load() should reject symlinks, even to valid JSON files.

    Before fix: load() follows symlink and reads the target file
    After fix: load() should raise ValueError when path is a symlink
    """
    # Create a legitimate JSON file with todos
    real_db = tmp_path / "real_todo.json"
    real_storage = TodoStorage(str(real_db))
    real_storage.save([Todo(id=1, text="legitimate todo")])

    # Create a symlink pointing to the real file
    symlink_db = tmp_path / "symlink_todo.json"
    symlink_db.symlink_to(real_db)

    # Attempt to load from symlink should fail
    symlink_storage = TodoStorage(str(symlink_db))
    with pytest.raises(ValueError, match=r"symlink|regular file"):
        symlink_storage.load()


def test_load_rejects_symlink_to_sensitive_file(tmp_path) -> None:
    """Issue #3362: load() should reject symlinks to non-JSON files.

    This prevents symlink attacks where an attacker creates a symlink
    from the database path to a sensitive system file.
    """
    # Create a fake sensitive file
    sensitive_file = tmp_path / "sensitive.txt"
    sensitive_file.write_text("SECRET_DATA=password123")

    # Create a symlink from database path to sensitive file
    symlink_db = tmp_path / "todo.json"
    symlink_db.symlink_to(sensitive_file)

    # Attempt to load should fail due to symlink rejection
    storage = TodoStorage(str(symlink_db))
    with pytest.raises(ValueError, match=r"symlink|regular file"):
        storage.load()


def test_load_accepts_regular_file(tmp_path) -> None:
    """Issue #3362: load() should work correctly with regular files.

    This ensures the fix doesn't break normal functionality.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save and load should work normally
    todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo", done=True)]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "test todo"
    assert loaded[1].text == "another todo"
    assert loaded[1].done is True


def test_load_returns_empty_for_nonexistent_file(tmp_path) -> None:
    """Issue #3362: load() should still return empty list for nonexistent files.

    This ensures the fix doesn't change existing behavior for missing files.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    loaded = storage.load()
    assert loaded == []


def test_load_rejects_directory(tmp_path) -> None:
    """Issue #3362: load() should reject directories.

    Directories are not regular files and should be rejected.
    """
    # Create a directory
    dir_path = tmp_path / "not_a_file"
    dir_path.mkdir()

    storage = TodoStorage(str(dir_path))
    with pytest.raises((ValueError, IsADirectoryError), match=r"regular file|directory|Is a directory"):
        storage.load()


def test_load_rejects_symlink_to_directory(tmp_path) -> None:
    """Issue #3362: load() should reject symlinks to directories.

    Even if the symlink points to a directory, it should be rejected.
    """
    # Create a directory
    dir_path = tmp_path / "real_directory"
    dir_path.mkdir()

    # Create a symlink to the directory
    symlink_db = tmp_path / "todo.json"
    symlink_db.symlink_to(dir_path)

    storage = TodoStorage(str(symlink_db))
    with pytest.raises(ValueError, match=r"symlink|regular file|directory"):
        storage.load()

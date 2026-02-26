"""Regression test for issue #5915: Potential TypeError if file_path has no parent.

This test verifies that TodoStorage.save() works correctly when the path
is a simple filename like 'todo.json' (no directory component), which results
in file_path.parent being '.' (current directory).

The bug was that _ensure_parent_directory tried to call mkdir('.') which
would fail with FileExistsError since '.' always exists.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_with_current_dir(tmp_path: Path) -> None:
    """Test _ensure_parent_directory handles current directory (.) correctly.

    When file_path is a simple filename like 'todo.json', parent is '.'.
    This should not raise any errors since '.' always exists.
    """
    # Change to tmp_path to ensure we're in a valid directory
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Simple filename with no directory component
        file_path = Path("todo.json")

        # This should not raise any errors
        _ensure_parent_directory(file_path)

        # The current directory should still exist
        assert Path(".").exists()
        assert Path(".").is_dir()
    finally:
        os.chdir(original_cwd)


def test_save_with_simple_filename_in_current_dir(tmp_path: Path) -> None:
    """Test TodoStorage.save() works with simple filename in current directory.

    This is the main regression test: saving to 'todo.json' (no directory)
    should work without errors.
    """
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Create storage with simple filename (no directory component)
        storage = TodoStorage("todo.json")
        todos = [Todo(id=1, text="test todo")]

        # This should work without raising FileExistsError or other errors
        storage.save(todos)

        # Verify file was created in current directory
        assert Path("todo.json").exists()

        # Verify we can load it back
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        os.chdir(original_cwd)


def test_save_with_explicit_current_dir_path(tmp_path: Path) -> None:
    """Test TodoStorage.save() works with explicit './todo.json' path."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Create storage with explicit current directory reference
        storage = TodoStorage("./todo.json")
        todos = [Todo(id=1, text="explicit dot path")]

        # This should work without errors
        storage.save(todos)

        # Verify file was created
        assert Path("todo.json").exists()

        # Verify content
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "explicit dot path"
    finally:
        os.chdir(original_cwd)


def test_ensure_parent_directory_with_subdir(tmp_path: Path) -> None:
    """Test _ensure_parent_directory still works correctly with subdirectories.

    This ensures the fix doesn't break normal directory creation.
    """
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Path with subdirectory
        file_path = Path("subdir/todo.json")

        # Parent doesn't exist yet
        assert not Path("subdir").exists()

        # This should create the parent directory
        _ensure_parent_directory(file_path)

        # Parent should now exist
        assert Path("subdir").exists()
        assert Path("subdir").is_dir()
    finally:
        os.chdir(original_cwd)

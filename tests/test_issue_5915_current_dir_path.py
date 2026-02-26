"""Regression tests for issue #5915: TypeError when file_path has no parent.

Issue: When file_path is a simple filename like 'todo.json' (without directory
component), file_path.parent returns '.' (current directory). Calling mkdir on
'.' with exist_ok=False raises FileExistsError because '.' always exists.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os
from pathlib import Path

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_handles_current_dir():
    """Issue #5915: Should not fail when parent is '.' (current directory).

    Before fix: parent.mkdir(parents=True, exist_ok=False) on '.' raises FileExistsError
    After fix: Should skip mkdir when parent is current directory (always exists)
    """
    # Use a simple filename without directory component
    file_path = Path("todo.json")

    # This should NOT raise an error
    # The parent is '.' which always exists by definition
    _ensure_parent_directory(file_path)


def test_storage_save_with_simple_filename(tmp_path):
    """Issue #5915: TodoStorage.save() should work with simple filename.

    This test verifies that saving works when path is just a filename
    without any directory component.
    """
    # Change to temp directory to avoid polluting repo
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Create storage with simple filename (no directory component)
        storage = TodoStorage("todo.json")

        # Save should work without errors
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # Verify file was created in current directory
        assert Path("todo.json").exists()

        # Verify we can load the data back
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        os.chdir(original_cwd)


def test_storage_save_with_explicit_current_dir(tmp_path):
    """Issue #5915: TodoStorage.save() should work with explicit './todo.json'.

    Using './todo.json' should work the same as 'todo.json'.
    """
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        storage = TodoStorage("./todo.json")

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        assert Path("todo.json").exists()
    finally:
        os.chdir(original_cwd)


def test_storage_default_path_is_simple_filename():
    """Issue #5915: Default path '.todo.json' should work without errors.

    The default storage path is '.todo.json' which has no parent directory.
    """
    original_cwd = os.getcwd()
    try:
        # Create a temp directory and change to it
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Use default path
            storage = TodoStorage()  # Uses default .todo.json

            todos = [Todo(id=1, text="default path test")]
            storage.save(todos)

            # Should have created .todo.json in current directory
            assert Path(".todo.json").exists()
    finally:
        os.chdir(original_cwd)

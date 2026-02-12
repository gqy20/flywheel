"""Regression tests for issue #2902: Cryptic error message when TodoStorage path is a directory.

Issue: When TodoStorage.path is a directory instead of a file, os.replace() raises
IsADirectoryError with message "[Errno 21] Is a directory" which is cryptic for end users.

Fix: Add validation in save() to check if self.path is a directory and raise
clear ValueError with message indicating path is a directory.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_fails_with_clear_error_when_path_is_directory(tmp_path) -> None:
    """Issue #2902: save() should raise clear ValueError when path is a directory.

    Before fix: os.replace raises IsADirectoryError with cryptic "[Errno 21] Is a directory"
    After fix: Should raise ValueError with message containing 'directory' and 'file'
    """
    # Create a directory where we expect a file
    directory_path = tmp_path / "mydb"
    directory_path.mkdir()

    # Create TodoStorage with the directory path
    storage = TodoStorage(str(directory_path))

    # save() should raise a clear ValueError
    with pytest.raises(ValueError, match=r"(directory|file)") as exc_info:
        storage.save([Todo(id=1, text="test")])

    # Error message should clearly indicate a file path is required
    error_message = str(exc_info.value).lower()
    assert "directory" in error_message, "Error message should mention 'directory'"


def test_save_fails_with_clear_error_for_existing_directory(tmp_path) -> None:
    """Issue #2902: save() should detect if path exists as directory."""
    # Create an existing directory
    existing_dir = tmp_path / "existing_dir"
    existing_dir.mkdir()

    storage = TodoStorage(str(existing_dir))

    with pytest.raises(ValueError, match=r"(directory|file)") as exc_info:
        storage.save([Todo(id=1, text="test")])

    # Verify error message is user-friendly
    error_message = str(exc_info.value).lower()
    assert "directory" in error_message


def test_save_works_when_path_is_file_in_directory(tmp_path) -> None:
    """Issue #2902: save() should work when path is a valid file path inside directory."""
    # Normal case: path points to a file inside a directory
    db_path = tmp_path / "todos.json"
    storage = TodoStorage(str(db_path))

    # This should work without error
    storage.save([Todo(id=1, text="test todo")])

    # Verify data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"

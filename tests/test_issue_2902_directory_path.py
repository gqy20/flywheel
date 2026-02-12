"""Regression test for issue #2902: Cryptic error message when TodoStorage path is a directory.

When TodoStorage.save() is called with a path that is an existing directory,
it should raise a clear ValueError instead of a cryptic IsADirectoryError.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_raises_clear_error_when_path_is_directory(tmp_path) -> None:
    """Test that save() raises clear ValueError when path is a directory.

    This is a regression test for issue #2902:
    When self.path points to an existing directory, os.replace raises
    IsADirectoryError with cryptic message "[Errno 21] Is a directory".

    The fix should validate that path is not a directory before attempting
    to write and raise a clear ValueError with user-friendly message.
    """
    # Create a directory to use as the storage path
    directory_path = tmp_path / "my_todos"
    directory_path.mkdir()

    storage = TodoStorage(str(directory_path))
    todos = [Todo(id=1, text="test todo")]

    # Should raise ValueError with clear message about directory
    with pytest.raises(ValueError, match="directory"):
        storage.save(todos)


def test_save_error_message_mentions_file_path_required(tmp_path) -> None:
    """Test that error message clearly states a file path is required."""
    directory_path = tmp_path / "another_dir"
    directory_path.mkdir()

    storage = TodoStorage(str(directory_path))
    todos = [Todo(id=1, text="test todo")]

    with pytest.raises(ValueError, match="file"):
        storage.save(todos)

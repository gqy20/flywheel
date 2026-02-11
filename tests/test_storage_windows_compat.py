"""Tests for Windows compatibility in TodoStorage.

This test suite verifies that TodoStorage.save() works correctly on Windows
where os.fchmod is not available.
"""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_without_fchmod(tmp_path) -> None:
    """Regression test for issue #2813: save should work when os.fchmod is unavailable.

    On Windows, os.fchmod is not available, causing an AttributeError.
    This test simulates that scenario by making os.fchmod unavailable.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2", done=True),
    ]

    # Simulate Windows environment where os.fchmod doesn't exist
    # Create a modified os module without fchmod
    import os as original_os
    mock_os = MagicMock(spec=original_os)
    # Copy all attributes from os to mock_os
    for attr in dir(original_os):
        if not attr.startswith("_"):
            with contextlib.suppress(AttributeError, TypeError):
                setattr(mock_os, attr, getattr(original_os, attr))
    # Explicitly remove fchmod to simulate Windows
    if hasattr(mock_os, "fchmod"):
        delattr(mock_os, "fchmod")

    with patch("flywheel.storage.os", mock_os):
        # This should not raise AttributeError
        storage.save(todos)

        # Verify file was created correctly
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "task 1"
        assert loaded[1].text == "task 2"
        assert loaded[1].done is True


def test_save_works_with_fchmod_available(tmp_path) -> None:
    """Test that save still works when os.fchmod is available (Unix-like systems)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="unix task"),
        Todo(id=2, text="another unix task"),
    ]

    # This should work normally on Unix-like systems with fchmod
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "unix task"
    assert loaded[1].text == "another unix task"

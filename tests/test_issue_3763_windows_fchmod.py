"""Regression test for issue #3763: os.fchmod not available on Windows.

This test verifies that TodoStorage.save() works correctly on Windows
where os.fchmod is not available.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Test that save() works when os.fchmod is not available (Windows).

    On Windows, os.fchmod does not exist and will raise AttributeError.
    The code should handle this gracefully by skipping the chmod call.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Simulate Windows by removing fchmod from os module
    import os

    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod to simulate Windows environment
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save(todos)

        # Verify the save was successful
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod

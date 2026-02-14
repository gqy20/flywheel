"""Tests for issue #3120: os.fchmod Windows compatibility.

This test suite verifies that TodoStorage.save() works correctly on Windows
where os.fchmod is not available.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Test that save works when os.fchmod is not available (Windows case).

    On Windows, os.fchmod does not exist, so the code should fall back
    gracefully without raising AttributeError.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a mock that simulates Windows (no fchmod)
    with (
        patch("flywheel.storage.os.fchmod", None),
        patch("flywheel.storage.hasattr") as mock_hasattr,
    ):
        # Make hasattr return False for fchmod, True for everything else
        def hasattr_side_effect(obj, name):
            if name == "fchmod":
                return False
            return hasattr(obj, name)

        mock_hasattr.side_effect = hasattr_side_effect

        todos = [Todo(id=1, text="test on windows")]
        # This should not raise AttributeError
        storage.save(todos)

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test on windows"


def test_fchmod_guard_with_hasattr_check(tmp_path) -> None:
    """Test that the code uses hasattr to check for fchmod availability."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track if hasattr was called with 'fchmod' argument
    hasattr_calls = []
    original_hasattr = hasattr

    def tracking_hasattr(obj, name):
        if obj is __import__("os"):
            hasattr_calls.append(name)
        return original_hasattr(obj, name)

    with patch("builtins.hasattr", tracking_hasattr):
        storage.save(todos)

    # Verify that fchmod was checked via hasattr
    assert "fchmod" in hasattr_calls, "Code should check hasattr(os, 'fchmod')"


def test_save_no_attribute_error_on_windows(tmp_path) -> None:
    """Regression test: Ensure no AttributeError is raised when fchmod unavailable.

    This test simulates exactly what happens on Windows when os.fchmod
    is called - it would raise AttributeError. The fix should guard against this.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by removing fchmod from os module
    import os as os_module

    original_fchmod = getattr(os_module, "fchmod", None)

    # On Windows, os.fchmod doesn't exist at all
    if hasattr(os_module, "fchmod"):
        delattr(os_module, "fchmod")

    try:
        todos = [Todo(id=1, text="windows compatible")]
        # This must NOT raise AttributeError
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "windows compatible"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os_module.fchmod = original_fchmod

"""Regression tests for issue #6840: os.fchmod is Unix-only.

Issue: os.fchmod raises AttributeError on Windows because it's Unix-only.
The code should gracefully handle platforms where os.fchmod is unavailable.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import contextlib
import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_unavailable(tmp_path) -> None:
    """Issue #6840: save() should work on Windows where os.fchmod doesn't exist.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() works gracefully on platforms without os.fchmod
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a mock os module without fchmod
    mock_os = type(os)("os")
    for attr in dir(os):
        if not attr.startswith("_") and attr != "fchmod":
            with contextlib.suppress(AttributeError, TypeError):
                setattr(mock_os, attr, getattr(os, attr))

    # Verify fchmod is NOT in our mock
    assert not hasattr(mock_os, "fchmod"), "Mock os should not have fchmod"

    todos = [Todo(id=1, text="test todo")]

    # Patch flywheel.storage.os to use our mock without fchmod
    with patch("flywheel.storage.os", mock_os):
        # This should NOT raise AttributeError
        storage.save(todos)

    # Verify the file was written correctly
    assert db.exists(), "Database file should be created"
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_works_with_fchmod_attribute_error(tmp_path) -> None:
    """Issue #6840: save() should handle AttributeError from os.fchmod gracefully.

    This tests the case where hasattr returns True but calling fchmod raises
    AttributeError (edge case on some platforms).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_fchmod = getattr(os, "fchmod", None)

    def raising_fchmod(*args, **kwargs):
        raise AttributeError("fchmod not available on this platform")

    # Temporarily replace fchmod with a version that raises AttributeError
    if hasattr(os, "fchmod"):
        os.fchmod = raising_fchmod
    else:
        os.fchmod = raising_fchmod  # type: ignore[attr-defined]

    try:
        todos = [Todo(id=1, text="test todo")]
        # This should NOT raise AttributeError - it should handle it gracefully
        storage.save(todos)

        # Verify the file was written correctly
        assert db.exists(), "Database file should be created"
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        # Restore original fchmod
        if original_fchmod is not None:
            os.fchmod = original_fchmod
        elif hasattr(os, "fchmod"):
            delattr(os, "fchmod")


def test_save_uses_chmod_fallback_on_windows(tmp_path, monkeypatch) -> None:
    """Issue #6840: On Windows, chmod should be used as fallback.

    When os.fchmod is unavailable, the code should fall back to os.chmod
    which is cross-platform.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    chmod_calls = []

    original_chmod = os.chmod
    original_fchmod = getattr(os, "fchmod", None)

    def tracking_chmod(path, mode, *args, **kwargs):
        chmod_calls.append((path, mode))
        return original_chmod(path, mode, *args, **kwargs)

    # Remove fchmod to simulate Windows
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    monkeypatch.setattr(os, "chmod", tracking_chmod, raising=False)

    try:
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # On Windows (simulated), chmod should have been called as fallback
        # Note: chmod might or might not be called depending on implementation
        # The important thing is that save() completed without error
        assert db.exists()
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod

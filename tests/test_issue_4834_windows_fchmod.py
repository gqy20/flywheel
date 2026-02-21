"""Regression test for issue #4834: os.fchmod is Unix-only.

This test verifies that TodoStorage.save() works correctly on Windows
by handling the absence of os.fchmod gracefully.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path: Path) -> None:
    """Test that save() works on Windows where os.fchmod is not available.

    Regression test for issue #4834: os.fchmod raises AttributeError on Windows.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Simulate Windows environment where os.fchmod does not exist
    import os

    # Save original if it exists
    original_fchmod = getattr(os, "fchmod", None)

    try:
        if hasattr(os, "fchmod"):
            delattr(os, "fchmod")

        # This should NOT raise AttributeError
        storage.save(todos)
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_uses_fchmod_when_available(tmp_path: Path) -> None:
    """Test that save() still uses fchmod on Unix systems where available."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Check if fchmod is available (Unix)
    import os

    if not hasattr(os, "fchmod"):
        pytest.skip("os.fchmod not available on this platform")

    # Track if fchmod was called
    original_fchmod = os.fchmod
    fchmod_called = []

    def tracking_fchmod(fd, mode):
        fchmod_called.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch.object(os, "fchmod", tracking_fchmod):
        storage.save(todos)

    # Verify fchmod was called with restrictive permissions
    assert len(fchmod_called) == 1
    # Mode should be 0o600 (owner read/write only)
    assert fchmod_called[0][1] == 0o600

    # Verify file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_completes_without_error_on_windows_simulated(tmp_path: Path) -> None:
    """Test that save() completes without AttributeError when fchmod is missing.

    This simulates Windows by raising AttributeError when fchmod is accessed,
    which is what actually happens on Windows.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="windows test")]

    # Delete fchmod from the os module to simulate Windows
    import os

    # Save original if it exists
    original_fchmod = getattr(os, "fchmod", None)

    try:
        if hasattr(os, "fchmod"):
            delattr(os, "fchmod")

        # This should NOT raise AttributeError
        storage.save(todos)

        # Verify the file was saved
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "windows test"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod

"""Regression test for issue #6731: os.fchmod is Unix-only, code will fail on Windows.

This test verifies that TodoStorage.save() works correctly on Windows
where os.fchmod is not available.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_without_fchmod_simulating_windows(tmp_path) -> None:
    """Test that save() works when os.fchmod is not available (Windows).

    On Windows, os.fchmod does not exist. This test simulates that
    environment by removing os.fchmod and verifying the code still works.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Simulate Windows by temporarily removing fchmod from os module
    import os

    original_fchmod = os.fchmod
    delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError - it should use os.chmod fallback
        storage.save(todos)
    finally:
        # Restore fchmod for other tests
        os.fchmod = original_fchmod

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_uses_fchmod_on_unix_when_available(tmp_path) -> None:
    """Test that save() uses os.fchmod on Unix when available.

    This ensures the fix doesn't break existing Unix behavior.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="unix test")]

    # Track if fchmod was called
    import os

    fchmod_called = []

    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_called.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch.object(os, "fchmod", tracking_fchmod):
        storage.save(todos)

    # Verify fchmod was called on Unix
    assert len(fchmod_called) == 1
    # Mode should be 0o600 (owner read/write only)
    assert fchmod_called[0][1] == 0o600

    # Verify file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "unix test"

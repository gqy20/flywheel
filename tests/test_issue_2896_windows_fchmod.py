"""Regression test for issue #2896: os.fchmod not available on Windows.

This test simulates the Windows environment where os.fchmod doesn't exist,
ensuring save() works without AttributeError.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_without_fchmod_simulating_windows(tmp_path: Path) -> None:
    """Test that save() works when os.fchmod is not available (Windows scenario).

    This is a regression test for issue #2896 where calling save() on Windows
    raised AttributeError because os.fchmod is Unix-only.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo")]

    # Simulate Windows environment where os.fchmod doesn't exist
    # We need to patch at the module level where it's used
    with patch("flywheel.storage.os") as mock_os:
        # Copy all attributes from real os module
        import os as real_os

        for attr in dir(real_os):
            if not attr.startswith("_") and hasattr(mock_os, attr):
                # Keep existing attributes (like replace, fdopen, unlink)
                continue
            elif not attr.startswith("_"):
                try:
                    setattr(mock_os, attr, getattr(real_os, attr))
                except (AttributeError, TypeError):
                    pass

        # Explicitly ensure fchmod raises AttributeError (like on Windows)
        del mock_os.fchmod

        # Ensure we have the necessary functions
        mock_os.replace = real_os.replace
        mock_os.fdopen = real_os.fdopen
        mock_os.unlink = real_os.unlink

        # Patch tempfile.mkstemp to use the real one
        import tempfile

        original_mkstemp = tempfile.mkstemp

        # This should NOT raise AttributeError
        storage.save(todos)

    # Verify the file was written correctly
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "test todo"
    assert loaded[1].text == "another todo"


def test_save_with_fchmod_unavailable_via_hasattr_mock(tmp_path: Path) -> None:
    """Test save() when hasattr(os, 'fchmod') returns False.

    Alternative approach: mock the module-level os to not have fchmod.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="windows compatible")]

    # Create a mock os module that doesn't have fchmod
    import os as real_os
    import tempfile

    class MockOS:
        """OS-like object without fchmod (simulating Windows)."""

        # Copy all attributes except fchmod
        def __init__(self):
            for attr in dir(real_os):
                if attr == "fchmod":
                    continue  # Skip fchmod - not on Windows
                if not attr.startswith("_"):
                    try:
                        setattr(self, attr, getattr(real_os, attr))
                    except (AttributeError, TypeError):
                        pass

    mock_os = MockOS()

    # Verify fchmod is not available
    assert not hasattr(mock_os, "fchmod")

    with patch("flywheel.storage.os", mock_os):
        # This should work without AttributeError
        storage.save(todos)

    # Verify data integrity
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "windows compatible"


def test_save_still_sets_restrictive_permissions_on_unix(tmp_path: Path) -> None:
    """Test that on Unix, save() still calls fchmod for restrictive permissions.

    This ensures the fix doesn't break Unix security behavior.
    """
    import os as real_os

    # Skip this test if fchmod is not available (we're on Windows)
    if not hasattr(real_os, "fchmod"):
        pytest.skip("os.fchmod not available on this platform")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="unix security test")]

    # Track if fchmod was called
    fchmod_calls = []
    original_fchmod = real_os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch("flywheel.storage.os.fchmod", tracking_fchmod):
        storage.save(todos)

    # On Unix, fchmod should have been called
    assert len(fchmod_calls) == 1
    fd, mode = fchmod_calls[0]
    # Mode should be 0o600 (owner read/write only)
    import stat

    expected_mode = stat.S_IRUSR | stat.S_IWUSR
    assert mode == expected_mode, f"Expected mode {expected_mode}, got {mode}"

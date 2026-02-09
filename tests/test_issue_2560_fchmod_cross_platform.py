"""Regression tests for issue #2560: os.fchmod fails on non-Unix platforms.

Issue: os.fchmod is only available on Unix platforms. On Windows, calling
os.fchmod raises AttributeError because the function doesn't exist.

The fix should:
1. Detect if os.fchmod is available (hasattr check)
2. Only call fchmod on Unix platforms
3. Work correctly on Windows without errors

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import builtins
import sys
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fchmod_not_called_on_windows(tmp_path) -> None:
    """Issue #2560: os.fchmod should not be called on Windows.

    On Windows, os.fchmod doesn't exist and would raise AttributeError.
    The code should detect platform and skip fchmod on Windows.
    """
    import os

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track whether fchmod was called
    fchmod_called = []

    def mock_fchmod(fd, mode):
        fchmod_called.append((fd, mode))
        raise AttributeError("fchmod not available on this platform")

    # Patch hasattr only in the storage module to avoid recursion
    original_hasattr = builtins.hasattr

    def side_hasattr(obj, name):
        if name == "fchmod" and obj is os:
            return False  # Simulate Windows: no fchmod
        return original_hasattr(obj, name)

    with (
        patch("flywheel.storage.hasattr", side_effect=side_hasattr),
        patch("flywheel.storage.os.fchmod", side_effect=mock_fchmod),
    ):
        # This should not call fchmod because hasattr returns False
        storage.save([Todo(id=1, text="test")])

    # Verify fchmod was NOT called
    assert len(fchmod_called) == 0, (
        f"os.fchmod was called {len(fchmod_called)} times on a platform "
        f"where it doesn't exist. This indicates missing cross-platform "
        f"compatibility check."
    )

    # Verify the file was actually saved
    assert db.exists(), "Database file should have been created"


def test_fchmod_works_on_unix_when_available(tmp_path) -> None:
    """Issue #2560: os.fchmod should work correctly on Unix platforms.

    On Unix, fchmod should still be called to set restrictive permissions.
    """
    import os
    import stat

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track fchmod calls
    fchmod_calls = []

    original_fchmod = getattr(os, "fchmod", None)

    if original_fchmod is not None:
        # Only test if fchmod is actually available (Unix)
        def tracking_fchmod(fd, mode):
            fchmod_calls.append((fd, mode))
            return original_fchmod(fd, mode)

        with patch("os.fchmod", side_effect=tracking_fchmod):
            storage.save([Todo(id=1, text="test")])

        # Verify fchmod was called with correct permissions on Unix
        if sys.platform != "win32" and hasattr(os, "fchmod"):
            assert len(fchmod_calls) > 0, "os.fchmod should have been called on Unix platforms"
            # Check that permissions were set to 0o600
            _fd, mode = fchmod_calls[0]
            assert mode == (stat.S_IRUSR | stat.S_IWUSR), (
                f"Expected permissions 0o600, got {oct(mode)}"
            )
    else:
        # On Windows or platforms without fchmod, just verify save works
        storage.save([Todo(id=1, text="test")])

    # Verify the file was saved regardless of platform
    assert db.exists(), "Database file should have been created"


def test_storage_save_works_on_all_platforms(tmp_path) -> None:
    """Issue #2560: TodoStorage.save should work on all platforms.

    This is an integration test ensuring the save operation completes
    successfully regardless of whether os.fchmod is available.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # This should work on any platform
    todos = [
        Todo(id=1, text="Task 1"),
        Todo(id=2, text="Task 2"),
    ]

    storage.save(todos)

    # Verify data was saved correctly
    assert db.exists(), "Database file should have been created"
    loaded = storage.load()
    assert len(loaded) == 2, "Should have loaded 2 todos"
    assert loaded[0].text == "Task 1"
    assert loaded[1].text == "Task 2"


def test_hasattr_os_fchmod_safe_check() -> None:
    """Issue #2560: Code should safely check for os.fchmod existence.

    This test verifies that hasattr(os, "fchmod") works correctly.
    """
    import os

    has_fchmod = hasattr(os, "fchmod")

    # On Unix, should be True
    # On Windows, should be False
    # The fix should use this check
    if sys.platform == "win32":
        assert not has_fchmod, "os.fchmod should not exist on Windows"
    else:
        # May or may not exist depending on Unix variant
        # hasattr should never raise an error
        assert isinstance(has_fchmod, bool)

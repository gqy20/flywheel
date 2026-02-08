"""Regression tests for issue #2248: os.fchmod() is Unix-only and will crash on Windows.

Issue: os.fchmod() is called unconditionally at src/flywheel/storage.py:112.
This function only exists on Unix platforms and will raise AttributeError on Windows.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_on_windows_platform(tmp_path) -> None:
    """Issue #2248: TodoStorage.save() should work on Windows without AttributeError.

    os.fchmod() doesn't exist on Windows. The code should detect this and
    skip the fchmod call, relying on mkstemp's default restrictive permissions.

    Before fix: AttributeError: module 'os' has no attribute 'fchmod'
    After fix: Works correctly on Windows
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by removing fchmod from os module
    # This should not raise AttributeError after the fix
    original_fchmod = getattr(os, "fchmod", None)

    # Create a mock that simulates Windows behavior (no fchmod attribute)
    if original_fchmod is not None:
        # Backup and remove fchmod to simulate Windows
        original_has_fchmod = True
        delattr(os, "fchmod")
    else:
        original_has_fchmod = False

    try:
        # This should NOT raise AttributeError on Windows simulation
        storage.save([Todo(id=1, text="test on windows")])

        # Verify data was actually saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test on windows"
    finally:
        # Restore fchmod if it existed before
        if original_has_fchmod:
            os.fchmod = original_fchmod


def test_save_fchmod_called_on_unix(tmp_path) -> None:
    """Issue #2248: Verify os.fchmod() IS called on Unix platforms for security.

    On Unix, the code should call fchmod to set 0o600 permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track if fchmod was called
    fchmod_calls = []

    original_fchmod = getattr(os, "fchmod", None)

    if original_fchmod is not None:
        # Track fchmod calls on Unix
        def tracking_fchmod(fd, mode):
            fchmod_calls.append((fd, mode))
            return original_fchmod(fd, mode)

        os.fchmod = tracking_fchmod
    else:
        # No fchmod on this platform (already Windows)
        # Test will be skipped effectively
        pass

    try:
        storage.save([Todo(id=3, text="unix test")])

        # On Unix with fchmod, it should have been called with 0o600
        if original_fchmod is not None:
            assert len(fchmod_calls) > 0, "fchmod should be called on Unix"
            _fd, mode = fchmod_calls[0]
            expected_mode = stat.S_IRUSR | stat.S_IWUSR  # 0o600
            assert mode == expected_mode, f"fchmod called with wrong mode: {oct(mode)}"

    finally:
        # Restore original fchmod
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_without_fchmod_still_works(tmp_path) -> None:
    """Issue #2248: Verify save works when fchmod is not available.

    When os.fchmod doesn't exist (Windows), the code should skip it
    and still successfully save the file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_fchmod = getattr(os, "fchmod", None)

    if original_fchmod is not None:
        original_has_fchmod = True
        delattr(os, "fchmod")
    else:
        original_has_fchmod = False

    try:
        # This should work without fchmod
        storage.save([Todo(id=4, text="no fchmod test")])

        # Verify data was saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "no fchmod test"
    finally:
        if original_has_fchmod:
            os.fchmod = original_fchmod

"""Regression tests for issue #5175: os.fchmod not available on Windows.

Issue: os.fchmod is not available on Windows, causing AttributeError when
calling it directly without platform compatibility checks.

The fix should use hasattr to check for os.fchmod before calling it.
On Windows, the file permissions are already secure by default when using
tempfile.mkstemp, so skipping fchmod is safe.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_does_not_call_fchmod_when_not_available(tmp_path) -> None:
    """Issue #5175: save() should not fail when os.fchmod is not available.

    Before fix: save() calls os.fchmod unconditionally, causing AttributeError
                on Windows where os.fchmod doesn't exist.
    After fix: save() checks hasattr(os, 'fchmod') before calling it.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    # by removing it from the os module temporarily
    original_fchmod = getattr(os, "fchmod", None)

    try:
        # Remove fchmod if it exists to simulate Windows behavior
        if hasattr(os, "fchmod"):
            delattr(os, "fchmod")

        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test on Windows-like environment")])

        # Verify the file was saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test on Windows-like environment"

    finally:
        # Restore original fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_still_sets_permissions_when_fchmod_available(tmp_path) -> None:
    """Issue #5175: When fchmod is available, permissions should still be set.

    This ensures the fix doesn't accidentally skip permission setting on Unix.
    """
    import stat

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Skip this test if fchmod is not available (e.g., running on Windows)
    if not hasattr(os, "fchmod"):
        import pytest
        pytest.skip("os.fchmod not available on this platform")

    # Track if fchmod was called
    fchmod_calls = []
    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    try:
        os.fchmod = tracking_fchmod
        storage.save([Todo(id=1, text="test")])
    finally:
        os.fchmod = original_fchmod

    # Verify fchmod was called with 0o600 permissions
    assert len(fchmod_calls) == 1, f"Expected 1 fchmod call, got {len(fchmod_calls)}"
    _fd, mode = fchmod_calls[0]
    assert mode == (stat.S_IRUSR | stat.S_IWUSR), (
        f"Expected mode 0o600, got {oct(mode)}"
    )


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Issue #5175: save() should handle missing fchmod gracefully.

    Regression test: Verify that the code uses hasattr/os.fchmod pattern
    instead of calling fchmod unconditionally.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Remove fchmod to simulate Windows
    original_fchmod = getattr(os, "fchmod", None)
    try:
        if hasattr(os, "fchmod"):
            delattr(os, "fchmod")

        # Should not raise AttributeError
        storage.save([Todo(id=1, text="cross-platform test")])

        # Verify save worked
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "cross-platform test"

    finally:
        if original_fchmod is not None:
            os.fchmod = original_fchmod

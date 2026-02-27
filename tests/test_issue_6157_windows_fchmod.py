"""Regression tests for issue #6157: os.fchmod is Unix-only.

Issue: os.fchmod is Unix-only and will raise AttributeError on Windows platforms.

The code should gracefully handle platforms where os.fchmod is not available
while still setting restrictive permissions on Unix systems.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_unavailable(tmp_path) -> None:
    """Issue #6157: save() should work when os.fchmod is not available.

    This simulates Windows behavior by removing fchmod from the os module.
    The save() method should complete successfully without raising AttributeError.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save the original fchmod (if it exists)
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod to simulate Windows
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError on Windows
        storage.save([Todo(id=1, text="test task")])

        # Verify the save was successful
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test task"
    finally:
        # Restore original fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_does_not_call_fchmod_when_unavailable(tmp_path) -> None:
    """Issue #6157: save() should not attempt to call fchmod if unavailable.

    This test ensures the code properly checks for fchmod availability
    before attempting to call it.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock os to not have fchmod
    original_fchmod = getattr(os, "fchmod", None)
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    # Track if any fchmod-related error occurs
    caught_attribute_error = False

    try:
        storage.save([Todo(id=1, text="test")])
    except AttributeError as e:
        if "fchmod" in str(e):
            caught_attribute_error = True
        raise
    finally:
        if original_fchmod is not None:
            os.fchmod = original_fchmod

    assert not caught_attribute_error, "Code should not raise AttributeError related to fchmod"


def test_save_sets_restrictive_permissions_on_unix(tmp_path) -> None:
    """Issue #6157: On Unix, save() should still set 0o600 permissions.

    This test verifies that the fix doesn't break the Unix behavior
    of setting restrictive file permissions.
    """
    import tempfile as tempfile_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_mkstemp = tempfile_module.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        # Check permissions after save completes (file will be renamed)
        return fd, path

    import tempfile

    original = tempfile.mkstemp
    tempfile.mkstemp = tracking_mkstemp

    try:
        storage.save([Todo(id=1, text="test")])
    finally:
        tempfile.mkstemp = original

    # On Unix with fchmod, verify the final file has restrictive permissions
    if hasattr(os, "fchmod"):
        file_stat = db.stat()
        file_mode = stat.S_IMODE(file_stat.st_mode)
        # The final file should have been created with restrictive permissions
        # Note: umask may affect the exact mode, but it should be owner-only
        assert (file_mode & 0o077) == 0, f"Final file has overly permissive mode: {oct(file_mode)}"

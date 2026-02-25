"""Regression tests for issue #5747: os.fchmod is Unix-only.

Issue: os.fchmod raises AttributeError on Windows because it's Unix-only.

This test simulates Windows behavior by mocking os.fchmod to not exist,
ensuring save() works cross-platform without AttributeError.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_succeeds_when_fchmod_unavailable(tmp_path) -> None:
    """Issue #5747: save() should succeed even when os.fchmod is unavailable.

    On Windows, os.fchmod doesn't exist and raises AttributeError.
    The code should handle this gracefully.

    Before fix: save() raises AttributeError on Windows
    After fix: save() succeeds without error
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save original fchmod reference if it exists
    original_fchmod = getattr(os, "fchmod", None)

    # Simulate Windows by removing fchmod from os module
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test")])

        # Verify the file was written correctly
        assert db.exists()
        content = db.read_text()
        assert '"text": "test"' in content
    finally:
        # Restore fchmod if it existed before
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_still_sets_permissions_on_unix(tmp_path) -> None:
    """Issue #5747: save() should still set 0o600 permissions on Unix.

    The fix should not break Unix permission setting behavior.
    This test only runs meaningful assertions on Unix systems.
    """
    # Skip actual permission check on Windows
    if not hasattr(os, "fchmod"):
        return

    import stat

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # Verify file was created with secure permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # On Unix, verify restrictive permissions (0o600 or similar)
    # The exact mode may vary due to umask, but group/others should have no permissions
    assert file_mode & 0o077 == 0, (
        f"File has overly permissive mode: {oct(file_mode)}. "
        f"Group/others should have no permissions."
    )

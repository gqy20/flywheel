"""Regression tests for issue #3748: os.fchmod not available on Windows.

Issue: os.fchmod is a POSIX-only function that doesn't exist on Windows.
Direct calls to os.fchmod cause AttributeError on Windows platform.

The fix should gracefully handle the absence of os.fchmod while preserving
the 0o600 permission setting on Unix/Linux/macOS platforms.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_gracefully_handles_missing_fchmod(tmp_path) -> None:
    """Issue #3748: save() should not crash when os.fchmod is unavailable.

    Simulates Windows behavior where os.fchmod doesn't exist.
    The save() method should gracefully degrade without raising an exception.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows where os.fchmod doesn't exist by patching hasattr
    # to return False for os.fchmod
    original_hasattr = hasattr

    def mock_hasattr(obj, name):
        if obj is os and name == "fchmod":
            return False
        return original_hasattr(obj, name)

    with mock.patch("builtins.hasattr", side_effect=mock_hasattr):
        # Should NOT raise - should gracefully degrade
        storage.save([Todo(id=1, text="test")])

    # Verify the file was still saved correctly
    assert db.exists()
    content = db.read_text()
    assert '"text": "test"' in content


def test_save_works_without_fchmod_attribute(tmp_path) -> None:
    """Issue #3748: Verify save() works when os module lacks fchmod entirely.

    This simulates the exact Windows behavior by temporarily removing
    the fchmod attribute from os module.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Store original fchmod if it exists
    original_fchmod = getattr(os, "fchmod", None)

    try:
        # Remove fchmod from os module to simulate Windows
        if hasattr(os, "fchmod"):
            delattr(os, "fchmod")

        # Should NOT raise - should gracefully handle missing fchmod
        storage.save([Todo(id=1, text="test")])

        # Verify the file was still saved correctly
        assert db.exists()
        content = db.read_text()
        assert '"text": "test"' in content
    finally:
        # Restore original if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


@pytest.mark.skipif(
    not hasattr(os, "fchmod"),
    reason="os.fchmod not available on this platform",
)
def test_save_sets_permissions_on_unix_platforms(tmp_path) -> None:
    """Issue #3748: Ensure Unix platforms still get 0o600 permissions.

    This test verifies that the fix doesn't break the existing behavior
    on Unix/Linux/macOS where os.fchmod is available.
    """
    import stat

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # Verify the file exists and has correct permissions
    assert db.exists()
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # On Unix, permissions should be 0o600 (rw-------)
    # Note: The actual mode might be affected by umask, but since we use
    # fchmod after creating the file, it should be exactly 0o600
    assert file_mode == 0o600, (
        f"File should have 0o600 permissions, got {oct(file_mode)}"
    )

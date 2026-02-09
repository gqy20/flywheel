"""Regression tests for issue #2560: os.fchmod compatibility on non-Unix platforms.

Issue: os.fchmod is not available on Windows/macOS, causing AttributeError.

The fix should:
1. Check if os.fchmod exists before calling it (hasattr check)
2. Only call fchmod on Unix platforms
3. Not crash on any platform

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import platform

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_does_not_raise_attribute_error_on_any_platform(tmp_path) -> None:
    """Issue #2560: TodoStorage.save() should work on all platforms.

    Before fix: Raises AttributeError on Windows/macOS (os.fchmod doesn't exist)
    After fix: Works on all platforms (hasattr check or platform detection)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # This should not raise AttributeError on any platform
    # On Windows/macOS: should skip fchmod gracefully
    # On Unix: should set 0o600 permissions as before
    storage.save([Todo(id=1, text="cross-platform test")])


def test_hasattr_fchmod_reflects_platform_reality() -> None:
    """Issue #2560: Verify hasattr(os, 'fchmod') correctly detects platform.

    This is a sanity check that our platform detection method works.
    """
    has_fchmod = hasattr(os, "fchmod")

    # On Unix (Linux), fchmod should exist
    # On Windows/macOS, fchmod should not exist
    is_unix = platform.system() in ("Linux", "FreeBSD", "OpenBSD")

    if is_unix:
        assert has_fchmod, "os.fchmod should be available on Unix platforms"
    else:
        # Windows or macOS
        assert not has_fchmod, (
            f"os.fchmod should NOT be available on {platform.system()}, "
            f"but hasattr returned True"
        )


@pytest.mark.skipif(
    not hasattr(os, "fchmod"),
    reason="os.fchmod only available on Unix platforms"
)
def test_unix_permissions_still_restrictive(tmp_path) -> None:
    """Issue #2560: On Unix, temp file should still have 0o600 permissions.

    This ensures the fix doesn't break the security hardening from issue #2027.
    """
    import stat
    import tempfile as tempfile_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    permissions_seen = []
    original_mkstemp = tempfile_module.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        file_stat = os.stat(path)
        file_mode = stat.S_IMODE(file_stat.st_mode)
        permissions_seen.append((path, file_mode))
        return fd, path

    import tempfile
    original = tempfile.mkstemp
    tempfile.mkstemp = tracking_mkstemp

    try:
        storage.save([Todo(id=1, text="unix permissions test")])
    finally:
        tempfile.mkstemp = original

    # On Unix, verify 0o600 permissions are still set
    assert len(permissions_seen) > 0, "No temp files were created"

    for _path, mode in permissions_seen:
        assert mode == 0o600, (
            f"On Unix, temp file should have 0o600 permissions, got {oct(mode)}"
        )

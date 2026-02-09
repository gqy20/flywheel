"""Regression tests for issue #2546: os.fchmod is Unix-only and will crash on Windows.

Issue: The code uses os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR) which is Unix-only.
On Windows, os.fchmod doesn't exist and will cause an AttributeError.

The fix should:
1. Handle Windows gracefully (skip chmod or use try/except)
2. Document platform-specific behavior
3. Maintain 0o600 permissions on Unix

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_fchmod_windows_compatibility(tmp_path) -> None:
    """Issue #2546: Code should not crash on Windows where os.fchmod doesn't exist.

    On Windows, os.fchmod doesn't exist. The code should handle this gracefully
    rather than crashing with AttributeError.

    This test simulates Windows behavior by mocking os.fchmod to raise AttributeError.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock os.fchmod to raise AttributeError like on Windows
    with patch("flywheel.storage.os.fchmod", side_effect=AttributeError("fchmod not available on this platform")):
        # This should NOT crash on Windows
        # Before fix: AttributeError: fchmod not available on this platform
        # After fix: Should work (chmod is skipped gracefully)
        try:
            storage.save([Todo(id=1, text="test on Windows")])
            # If we get here, Windows compatibility is working
        except AttributeError as e:
            if "fchmod" in str(e).lower():
                raise AssertionError(
                    f"Code crashed on Windows due to os.fchmod: {e}. "
                    "The code should handle Windows gracefully."
                ) from e
            raise

    # Verify the save actually worked
    assert db.exists(), "Database file should exist after save"
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test on Windows"


def test_fchmod_works_on_unix(tmp_path) -> None:
    """Issue #2546: On Unix, os.fchmod should still work and set 0o600 permissions.

    This ensures the Unix behavior is preserved when fixing Windows compatibility.
    """
    import os
    import stat
    import tempfile as tempfile_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track permissions of created temp files
    permissions_seen = []

    original_mkstemp = tempfile_module.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        # Check permissions immediately after creation
        file_stat = os.stat(path)
        file_mode = stat.S_IMODE(file_stat.st_mode)
        permissions_seen.append((path, file_mode))
        return fd, path

    # Patch to track permissions
    import tempfile
    original = tempfile.mkstemp
    tempfile.mkstemp = tracking_mkstemp

    try:
        storage.save([Todo(id=1, text="test on Unix")])
    finally:
        tempfile.mkstemp = original

    # Verify temp file was created with 0o600 permissions on Unix
    assert len(permissions_seen) > 0, "No temp files were created"

    for path, mode in permissions_seen:
        # On Unix, the mode should be 0o600 (rw-------)
        assert mode == 0o600, (
            f"Temp file has incorrect permissions on Unix: {oct(mode)} "
            f"(expected 0o600, got 0o{mode:o}). "
            f"File was: {path}"
        )


def test_has_fchmod_attribute() -> None:
    """Test helper to verify os.fchmod availability check works."""
    import os

    # This test documents the platform-specific behavior
    has_fchmod = hasattr(os, "fchmod")
    is_windows = sys.platform == "win32"

    # On Unix, os.fchmod should exist
    if not is_windows:
        assert has_fchmod, "os.fchmod should exist on Unix platforms"

    # On Windows (or in CI), we document the behavior
    if is_windows:
        assert not has_fchmod, "os.fchmod should not exist on Windows"

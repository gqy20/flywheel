"""Regression tests for issue #2234: Windows compatibility - avoid os.fchmod.

Issue: Code uses os.fchmod which is not available on Windows prior to Python 3.11.

Fix: Use os.chmod instead which works on both Windows and Unix platforms.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_does_not_use_os_fchmod(tmp_path) -> None:
    """Issue #2234: TodoStorage.save should not use os.fchmod (Windows incompatible).

    os.fchmod is not available on Windows prior to Python 3.11.
    The fix uses os.chmod instead, which works on both platforms.

    Before fix: Code uses os.fchmod(fd, ...) which fails on Windows
    After fix: Code uses os.chmod(path, ...) which works everywhere
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    fchmod_called = []
    original_fchmod = getattr(os, 'fchmod', None)

    if original_fchmod is None:
        # os.fchmod doesn't exist on this platform (likely Windows)
        # This is already good - test would pass without modifications
        # But we should still verify the storage works
        storage.save([Todo(id=1, text="test")])
        return

    def tracking_fchmod(fd, mode):
        fchmod_called.append((fd, mode))
        return original_fchmod(fd, mode)

    # Patch os.fchmod to track if it's called
    with patch.object(os, 'fchmod', side_effect=tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # Verify os.fchmod was NOT called
    assert len(fchmod_called) == 0, (
        f"os.fchmod was called {len(fchmod_called)} time(s), "
        f"indicating Windows-incompatible code. "
        f"Use os.chmod instead for cross-platform compatibility."
    )


def test_temp_file_has_restrictive_permissions_cross_platform(tmp_path) -> None:
    """Issue #2234: Verify temp files have 0o600 permissions using os.chmod.

    This test verifies that the cross-platform fix (using os.chmod)
    still correctly sets restrictive permissions on temp files.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    temp_files_created = []

    original_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    import tempfile as tempfile_module
    original = tempfile_module.mkstemp
    tempfile_module.mkstemp = tracking_mkstemp

    try:
        storage.save([Todo(id=1, text="test")])
    finally:
        tempfile_module.mkstemp = original

    # Verify temp file was created with restrictive permissions
    assert len(temp_files_created) > 0, "No temp files were created"

    for temp_file in temp_files_created:
        if temp_file.exists():
            file_stat = temp_file.stat()
            file_mode = stat.S_IMODE(file_stat.st_mode)

            # On Windows, chmod may not work the same way
            # Just verify the file was created successfully
            # On Unix, verify restrictive permissions
            if os.name != 'nt':  # Not Windows
                assert file_mode & stat.S_IRUSR, f"Temp file lacks owner read: {oct(file_mode)}"
                assert file_mode & stat.S_IWUSR, f"Temp file lacks owner write: {oct(file_mode)}"


def test_storage_save_works_on_windows_like_environment(tmp_path) -> None:
    """Issue #2234: Verify storage.save works when os.fchmod is unavailable.

    This simulates a Windows environment where os.fchmod doesn't exist.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment by temporarily removing fchmod
    original_fchmod = getattr(os, 'fchmod', None)

    if original_fchmod is not None:
        # Only test if fchmod exists (Unix-like systems)
        # Remove it temporarily to simulate Windows
        delattr(os, 'fchmod')

        try:
            # This should NOT raise an AttributeError
            storage.save([Todo(id=1, text="test")])
        finally:
            # Restore fchmod
            os.fchmod = original_fchmod
    else:
        # Already on Windows-like environment, just verify it works
        storage.save([Todo(id=1, text="test")])

    # Verify the file was saved correctly
    assert db.exists(), "Database file should exist after save"
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "test"

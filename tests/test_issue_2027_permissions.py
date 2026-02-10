"""Regression tests for issue #2027: Temp file permissions should be exactly 0o600.

Issue: Code uses stat.S_IRWXU (0o700 - rwx------) but comment promises 0o600 (rw-------).

The temp file should NOT have the execute bit set. A temp file containing
JSON data doesn't need to be executable, and having execute permissions
is unnecessary security surface area.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_temp_file_has_no_execute_bit(tmp_path) -> None:
    """Issue #2027: Temp file should have exactly 0o600 permissions (rw-------).

    The current code uses stat.S_IRWXU which is 0o700 (rwx------), including
    the execute bit. Temp files don't need execute permissions.

    Before fix: Temp file has 0o700 (rwx------) - execute bit is set
    After fix: Temp file has 0o600 (rw-------) - no execute bit
    """
    import tempfile as tempfile_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), _base_dir=tmp_path)

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
        storage.save([Todo(id=1, text="test")])
    finally:
        tempfile.mkstemp = original

    # Verify temp file was created with EXACTLY 0o600 permissions
    assert len(permissions_seen) > 0, "No temp files were created"

    for path, mode in permissions_seen:
        # The mode should be EXACTLY 0o600 (rw-------)
        assert mode == 0o600, (
            f"Temp file has incorrect permissions: {oct(mode)} "
            f"(expected 0o600, got 0o{mode:o}). "
            f"File was: {path}"
        )

        # Specifically verify no execute bit is set
        assert not (mode & stat.S_IXUSR), (
            f"Temp file should not have owner execute bit set. "
            f"Mode: {oct(mode)}, File: {path}"
        )

        # Verify owner can read and write
        assert mode & stat.S_IRUSR, f"Temp file lacks owner read: {oct(mode)}"
        assert mode & stat.S_IWUSR, f"Temp file lacks owner write: {oct(mode)}"

        # Verify group and others have no permissions
        assert mode & 0o077 == 0, f"Temp file has overly permissive mode: {oct(mode)}"


def test_temp_file_is_not_executable(tmp_path) -> None:
    """Issue #2027: Temp file containing JSON should not be executable.

    This is a security-focused test. Data files should never be executable.
    """
    import tempfile as tempfile_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), _base_dir=tmp_path)

    temp_files_created = []

    original_mkstemp = tempfile_module.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    import tempfile
    original = tempfile.mkstemp
    tempfile.mkstemp = tracking_mkstemp

    try:
        storage.save([Todo(id=1, text="test")])
    finally:
        tempfile.mkstemp = original

    # Verify none of the temp files have execute permissions
    for temp_file in temp_files_created:
        if temp_file.exists():
            file_stat = temp_file.stat()
            file_mode = stat.S_IMODE(file_stat.st_mode)

            # Check that no execute bits are set for anyone
            assert not (file_mode & stat.S_IXUSR), f"Owner execute bit set on {temp_file}"
            assert not (file_mode & stat.S_IXGRP), f"Group execute bit set on {temp_file}"
            assert not (file_mode & stat.S_IXOTH), f"Other execute bit set on {temp_file}"

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


def test_final_file_has_restrictive_permissions(tmp_path) -> None:
    """Issue #7063: Final database file should have 0o600 permissions.

    After os.replace(), the final file should have restrictive permissions
    (0o600 - rw-------) to prevent other users from reading the todo database.

    This test ensures the explicit os.chmod() call after os.replace() is working.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo to create the database file
    storage.save([Todo(id=1, text="test")])

    # Verify the final file exists
    assert db.exists(), "Final database file should exist after save"

    # Check final file permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o})"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify no execute bit is set
    assert not (file_mode & stat.S_IXUSR), (
        f"Final file should not have owner execute bit set. Mode: {oct(file_mode)}"
    )

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, f"Final file has overly permissive mode: {oct(file_mode)}"


def test_final_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #7063: Final file permissions should remain 0o600 on subsequent saves.

    When overwriting an existing database file, the permissions should still
    be set to 0o600 after the atomic rename.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create the database with first save
    storage.save([Todo(id=1, text="first")])
    first_mode = stat.S_IMODE(db.stat().st_mode)
    assert first_mode == 0o600, f"First save: expected 0o600, got {oct(first_mode)}"

    # Overwrite with second save
    storage.save([Todo(id=2, text="second")])
    second_mode = stat.S_IMODE(db.stat().st_mode)
    assert second_mode == 0o600, f"Second save: expected 0o600, got {oct(second_mode)}"


def test_temp_file_is_not_executable(tmp_path) -> None:
    """Issue #2027: Temp file containing JSON should not be executable.

    This is a security-focused test. Data files should never be executable.
    """
    import tempfile as tempfile_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

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

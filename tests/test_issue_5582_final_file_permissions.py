"""Regression tests for issue #5582: Final database file permissions should be 0o600.

Issue: Final database file permissions not explicitly set after atomic rename.
The temp file has 0o600 permissions but after os.replace(), the final file
may have different permissions depending on filesystem/umask.

Security: Database files should have restrictive permissions (0o600) to prevent
other users from reading sensitive todo data.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_database_file_has_0600_permissions(tmp_path) -> None:
    """Issue #5582: Final database file should have exactly 0o600 permissions.

    The temp file is created with 0o600 permissions, but os.replace() may not
    preserve these permissions on all platforms (e.g., some NFS mounts, Windows).

    Before fix: Final file permissions depend on filesystem/umask
    After fix: Final file has exactly 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo item
    storage.save([Todo(id=1, text="sensitive data")])

    # Verify the final database file has exactly 0o600 permissions
    assert db.exists(), "Database file should exist after save"

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600). This is a security issue - other users may be able "
        f"to read sensitive todo data."
    )


def test_final_database_file_permissions_persist_across_saves(tmp_path) -> None:
    """Issue #5582: Permissions should remain 0o600 across multiple saves.

    This ensures the fix is applied consistently on every save operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])
    file_stat = db.stat()
    assert stat.S_IMODE(file_stat.st_mode) == 0o600, (
        f"First save: permissions should be 0o600, got {oct(file_stat.st_mode)}"
    )

    # Second save (overwrites)
    storage.save([Todo(id=1, text="first"), Todo(id=2, text="second")])
    file_stat = db.stat()
    assert stat.S_IMODE(file_stat.st_mode) == 0o600, (
        f"Second save: permissions should be 0o600, got {oct(file_stat.st_mode)}"
    )

    # Third save (different content)
    storage.save([Todo(id=3, text="third")])
    file_stat = db.stat()
    assert stat.S_IMODE(file_stat.st_mode) == 0o600, (
        f"Third save: permissions should be 0o600, got {oct(file_stat.st_mode)}"
    )


def test_final_database_file_no_execute_bit(tmp_path) -> None:
    """Issue #5582: Final database file should not be executable.

    Data files should never have execute permissions - this is a security best practice.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify no execute bits are set
    assert not (file_mode & stat.S_IXUSR), "Owner execute bit should not be set"
    assert not (file_mode & stat.S_IXGRP), "Group execute bit should not be set"
    assert not (file_mode & stat.S_IXOTH), "Other execute bit should not be set"


def test_final_database_file_no_group_or_other_permissions(tmp_path) -> None:
    """Issue #5582: Final database file should not allow group/other access.

    Only the owner should be able to read/write the database file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="secret")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Group and others should have no permissions
    assert (file_mode & 0o077) == 0, (
        f"Final database file has group or other permissions: {oct(file_mode)}. "
        f"Only owner should have access (expected 0o600)."
    )

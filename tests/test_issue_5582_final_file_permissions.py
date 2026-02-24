"""Regression tests for issue #5582: Final database file permissions should be 0o600.

Issue: Final database file permissions not explicitly set after atomic rename.
The temp file has 0o600 but the final file may have different permissions
depending on filesystem/umask, especially on some NFS mounts or Windows.

The fix ensures final file has exactly 0o600 permissions after save() completes.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restricted_permissions(tmp_path) -> None:
    """Issue #5582: Final database file should have exactly 0o600 permissions.

    After save() completes, the final file (self.path) must have restrictive
    permissions (0o600 = rw-------) to prevent unauthorized access.

    Before fix: Final file may inherit system umask or have permissive defaults
    After fix: Final file has explicitly set 0o600 (rw-------) permissions
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    storage.save([Todo(id=1, text="test todo")])

    # Verify the final file exists
    assert db.exists(), "Final database file should exist after save()"

    # Get the final file's permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"File was: {db}"
    )

    # Specifically verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify no execute bit is set
    assert not (file_mode & stat.S_IXUSR), (
        f"Final file should not have owner execute bit set. Mode: {oct(file_mode)}, File: {db}"
    )

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, (
        f"Final file has overly permissive mode: {oct(file_mode)}. "
        f"Group and others should have no permissions."
    )


def test_final_file_permissions_after_overwrite(tmp_path) -> None:
    """Issue #5582: Final file should maintain 0o600 permissions after overwrite.

    When overwriting an existing database file, the final file should still
    have exactly 0o600 permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="initial todo")])

    # Overwrite with new data
    storage.save(
        [
            Todo(id=1, text="updated todo"),
            Todo(id=2, text="new todo"),
        ]
    )

    # Verify final permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions after overwrite: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o})"
    )


def test_final_file_permissions_not_executable(tmp_path) -> None:
    """Issue #5582: Final database file should never be executable.

    This is a security-focused test. Data files should never be executable.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Check that no execute bits are set for anyone
    assert not (file_mode & stat.S_IXUSR), f"Owner execute bit set on {db}"
    assert not (file_mode & stat.S_IXGRP), f"Group execute bit set on {db}"
    assert not (file_mode & stat.S_IXOTH), f"Other execute bit set on {db}"


def test_final_file_permissions_explicitly_set_after_rename(tmp_path) -> None:
    """Issue #5582: Final file permissions should be explicitly set after rename.

    This test simulates a scenario where os.replace() might not preserve
    permissions (e.g., on some NFS mounts or Windows). The fix should
    explicitly chmod the final file to ensure 0o600 permissions.

    We mock os.replace to simulate a scenario where permissions are lost
    during rename, then verify the fix explicitly sets correct permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_replace = os.replace

    def replace_with_lost_permissions(src, dst):
        """Simulate os.replace that doesn't preserve permissions."""
        result = original_replace(src, dst)
        # Simulate a filesystem that resets permissions during rename
        # (e.g., umask applied, or Windows ACL behavior)
        if Path(dst).exists():
            os.chmod(dst, 0o644)  # Simulate permissive default
        return result

    with mock.patch.object(os, "replace", replace_with_lost_permissions):
        storage.save([Todo(id=1, text="test")])

    # After the fix, final file should have 0o600 despite rename losing permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final database file should have 0o600 permissions after explicit chmod. "
        f"Got: {oct(file_mode)}. This indicates os.chmod was not called after os.replace."
    )

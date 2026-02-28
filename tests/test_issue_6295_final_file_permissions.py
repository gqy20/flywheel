"""Regression tests for issue #6295: Final db file permissions should be 0o600.

Issue: The temp file gets 0o600 permissions, but after os.replace() the final
db file may not retain these permissions on some systems. This is a security
vulnerability that could expose sensitive todo data to other users.

The fix ensures the final db file has restrictive 0o600 permissions (rw-------)
regardless of system umask or filesystem behavior.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_db_file_has_restricted_permissions(tmp_path: Path) -> None:
    """Issue #6295: Final db file should have 0o600 permissions (rw-------).

    The temp file gets 0o600, but os.replace() may not preserve permissions
    on all systems. We must explicitly set permissions on the final file.

    Security requirement: Only owner should be able to read/write the db file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    storage.save([Todo(id=1, text="secret task"), Todo(id=2, text="another secret")])

    # Check final file permissions
    assert db.exists(), "Final db file should exist"

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final db file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"This is a security vulnerability - other users could read your todos."
    )


def test_final_db_file_permissions_after_overwrite(tmp_path: Path) -> None:
    """Issue #6295: Final db file should maintain 0o600 after overwrites.

    This test verifies that even if a file exists with overly permissive
    permissions (e.g., due to a previous bug or manual chmod), saving again
    will ensure the final file has secure 0o600 permissions.

    The fix explicitly sets permissions after os.replace() as a defense-in-depth
    measure, since os.replace() permission preservation behavior may vary across
    filesystems and platforms.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Manually change permissions to something more permissive
    # (simulating a scenario where permissions got changed or file was created
    # with different umask)
    db.chmod(0o644)

    # Verify permissions are now wrong
    wrong_mode = stat.S_IMODE(db.stat().st_mode)
    assert wrong_mode == 0o644, f"Setup failed: permissions should be 0o644, got {oct(wrong_mode)}"

    # Save again - this should fix the permissions
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])

    # Verify permissions are now correct
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final db file permissions not fixed after overwrite: {oct(file_mode)} "
        f"(expected 0o600). This is a security vulnerability."
    )


def test_final_db_file_permissions_explicitly_set_after_replace(tmp_path: Path) -> None:
    """Issue #6295: Verify chmod is called on final file after os.replace().

    This is a regression test that verifies the fix is in place by mocking
    os.chmod to ensure it's called with the correct arguments after save.
    """
    from unittest.mock import patch

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    chmod_calls = []

    def tracking_chmod(path, mode, *args, **kwargs):
        chmod_calls.append((str(path), mode))
        return original_chmod(path, mode, *args, **kwargs)

    original_chmod = os.chmod

    with patch("flywheel.storage.os.chmod", side_effect=tracking_chmod):
        storage.save([Todo(id=1, text="test")])

    # Verify chmod was called on the final file with 0o600
    assert len(chmod_calls) > 0, "os.chmod should have been called"

    # Find the call for our db file
    db_str = str(db)
    found = False
    for path, mode in chmod_calls:
        if path == db_str or path.endswith("todo.json"):
            assert mode == 0o600, (
                f"os.chmod called with wrong mode: {oct(mode)} instead of 0o600"
            )
            found = True
            break

    assert found, f"os.chmod should have been called on {db_str}, got calls: {chmod_calls}"


def test_final_db_file_no_group_or_other_access(tmp_path: Path) -> None:
    """Issue #6295: Final db file should not allow group or other access.

    Security-focused test: verify that neither group nor others can access
    the database file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="confidential")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify no group permissions
    assert not (file_mode & stat.S_IRGRP), f"Group read bit should not be set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWGRP), f"Group write bit should not be set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXGRP), f"Group execute bit should not be set: {oct(file_mode)}"

    # Verify no other permissions
    assert not (file_mode & stat.S_IROTH), f"Other read bit should not be set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWOTH), f"Other write bit should not be set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXOTH), f"Other execute bit should not be set: {oct(file_mode)}"


def test_final_db_file_owner_can_read_and_write(tmp_path: Path) -> None:
    """Issue #6295: Owner should still be able to read and write the file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Owner should have read and write
    assert file_mode & stat.S_IRUSR, f"Owner should have read permission: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Owner should have write permission: {oct(file_mode)}"

    # Owner should NOT have execute (data files don't need it)
    assert not (file_mode & stat.S_IXUSR), f"Owner should not have execute permission: {oct(file_mode)}"

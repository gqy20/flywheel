"""Regression tests for issue #4368: Final file permissions should be 0o600.

Issue: Only temp file gets restrictive mode 0o600, final file may not have
restrictive permissions after os.replace(). The temp file's permissions are
lost after rename on some systems.

Security: The final .todo.json file should have 0o600 (rw-------) or more
restrictive permissions to ensure other users cannot read the todo database.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restricted_permissions(tmp_path) -> None:
    """Issue #4368: Final file should have exactly 0o600 permissions (rw-------).

    After save() completes, the final .todo.json file should have restrictive
    permissions (0o600) to prevent other users from reading the todo database.

    Before fix: Final file may inherit umask or parent directory permissions
    After fix: Final file has exactly 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo item
    storage.save([Todo(id=1, text="test")])

    # Verify final file has exactly 0o600 permissions
    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o})"
    )

    # Specifically verify no execute bit is set
    assert not (file_mode & stat.S_IXUSR), (
        f"Final file should not have owner execute bit set. "
        f"Mode: {oct(file_mode)}"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, f"Final file has overly permissive mode: {oct(file_mode)}"


def test_final_file_group_others_no_access(tmp_path) -> None:
    """Issue #4368: Group and others should have no permissions on final file.

    Security-focused test ensuring that group and other users cannot read
    the todo database.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo item
    storage.save([Todo(id=1, text="secret task")])

    # Get final file permissions
    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify group has no permissions
    assert not (file_mode & stat.S_IRGRP), f"Group has read permission: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWGRP), f"Group has write permission: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXGRP), f"Group has execute permission: {oct(file_mode)}"

    # Verify others have no permissions
    assert not (file_mode & stat.S_IROTH), f"Others have read permission: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWOTH), f"Others have write permission: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXOTH), f"Others have execute permission: {oct(file_mode)}"


def test_final_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #4368: Final file permissions should remain 0o600 after overwrites.

    When overwriting an existing file, the permissions should still be 0o600.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])

    # Verify initial permissions
    first_stat = os.stat(db)
    first_mode = stat.S_IMODE(first_stat.st_mode)
    assert first_mode == 0o600, f"First save: expected 0o600, got {oct(first_mode)}"

    # Overwrite with more data
    storage.save([Todo(id=1, text="first"), Todo(id=2, text="second")])

    # Verify permissions are still 0o600 after overwrite
    second_stat = os.stat(db)
    second_mode = stat.S_IMODE(second_stat.st_mode)
    assert second_mode == 0o600, f"After overwrite: expected 0o600, got {oct(second_mode)}"

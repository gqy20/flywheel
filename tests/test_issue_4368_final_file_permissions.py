"""Regression tests for issue #4368: Final file permissions should be 0o600.

Issue: Only temp file gets restrictive mode 0o600, final file may inherit umask
or parent directory defaults on some systems after os.replace().

The final .todo.json file should have exactly 0o600 permissions (rw-------)
to prevent other users from reading the todo database.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_0o600_permissions(tmp_path) -> None:
    """Issue #4368: Final file should have exactly 0o600 permissions (rw-------).

    After storage.save() completes, the final .todo.json file should have
    restrictive permissions to protect user data from other users on the system.

    Before fix: Final file may have default umask permissions (e.g., 0o644)
    After fix: Final file has exactly 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo
    storage.save([Todo(id=1, text="secret todo item")])

    # Check the FINAL file permissions (not temp file)
    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"File was: {db}"
    )

    # Specifically verify no execute bit is set
    assert not (file_mode & stat.S_IXUSR), (
        f"Final file should not have owner execute bit set. "
        f"Mode: {oct(file_mode)}, File: {db}"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, f"Final file has overly permissive mode: {oct(file_mode)}"


def test_final_file_permissions_after_overwrite(tmp_path) -> None:
    """Issue #4368: Final file permissions should remain 0o600 after overwriting.

    When overwriting an existing file, the permissions should still be 0o600.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - creates file
    storage.save([Todo(id=1, text="first todo")])

    # Verify initial permissions
    initial_mode = stat.S_IMODE(os.stat(db).st_mode)
    assert initial_mode == 0o600, f"Initial file permissions wrong: {oct(initial_mode)}"

    # Second save - overwrites file
    storage.save([Todo(id=1, text="updated todo"), Todo(id=2, text="new todo")])

    # Verify permissions are still 0o600 after overwrite
    final_mode = stat.S_IMODE(os.stat(db).st_mode)
    assert final_mode == 0o600, (
        f"Final file permissions wrong after overwrite: {oct(final_mode)} "
        f"(expected 0o600)"
    )


def test_final_file_not_readable_by_others(tmp_path) -> None:
    """Issue #4368: Other users should not be able to read the todo database.

    This is the security goal - the file should not be readable by group or others.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save sensitive data
    storage.save([Todo(id=1, text="private api key: sk-12345")])

    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify group and others have NO read permissions
    assert not (file_mode & stat.S_IRGRP), (
        f"Final file should not be group-readable. Mode: {oct(file_mode)}"
    )
    assert not (file_mode & stat.S_IROTH), (
        f"Final file should not be other-readable. Mode: {oct(file_mode)}"
    )

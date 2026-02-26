"""Regression tests for issue #5880: Final database file permissions should be 0o600.

Issue: The temp file is created with restrictive 0o600 permissions, but after
os.replace(), the final file's permissions may not be guaranteed to be 0o600.
On some systems/configurations, this may result in the final file having
less restrictive permissions.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restricted_permissions(tmp_path) -> None:
    """Issue #5880: Final database file should have 0o600 permissions (rw-------).

    After save() completes, the final .json file should have exactly 0o600
    permissions, matching the security posture of the temp file.

    Before fix: Final file may have default permissions (e.g., 0o644)
    After fix: Final file has 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo to create the database file
    storage.save([Todo(id=1, text="test todo")])

    # Verify the final file exists
    assert db.exists(), "Final database file should exist"

    # Get the permissions of the final file
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600). File: {db}"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify no execute bit is set
    assert not (file_mode & stat.S_IXUSR), (
        f"Final file should not have owner execute bit set. Mode: {oct(file_mode)}"
    )

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, (
        f"Final file has overly permissive mode: {oct(file_mode)}. "
        f"Only owner should have access."
    )


def test_final_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #5880: Permissions should remain 0o600 when overwriting existing file.

    When saving to an existing database file, the permissions should remain
    at 0o600, not revert to less restrictive permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="first todo")])

    # Verify initial permissions
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o600, f"Initial file should have 0o600, got {oct(initial_mode)}"

    # Overwrite the file
    storage.save([Todo(id=1, text="updated todo"), Todo(id=2, text="new todo")])

    # Verify permissions are still restricted after overwrite
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == 0o600, (
        f"After overwrite, permissions should remain 0o600, got {oct(final_mode)}"
    )

"""Regression tests for issue #5880: Final database file permissions should be 0o600.

Issue: The temp file is created with restrictive 0o600 permissions, but after
os.replace(), the final file may inherit different permissions. Should explicitly
set permissions on the final file after replace to ensure consistent security.

Security: Database files containing todo items may contain sensitive data.
They should have restrictive permissions (0o600 - rw-------) to prevent
other users from reading the file contents.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restricted_permissions(tmp_path) -> None:
    """Issue #5880: Final database file should have 0o600 permissions (rw-------).

    After save() completes, the final .todo.json file should have the same
    restrictive permissions as the temp file (0o600).

    Before fix: Final file may have default umask permissions (e.g., 0o644)
    After fix: Final file has 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo item
    storage.save([Todo(id=1, text="secret todo item")])

    # Check the final file permissions
    assert db.exists(), "Final database file should exist"
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600). Security: other users may be able to read sensitive data."
    )


def test_final_file_permissions_after_overwrite(tmp_path) -> None:
    """Issue #5880: Final file should maintain 0o600 permissions after overwrite.

    When overwriting an existing file, permissions should still be restricted.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Overwrite with new content
    storage.save([Todo(id=1, text="initial"), Todo(id=2, text="second")])

    # Verify permissions are still restricted
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final database file lost restrictive permissions after overwrite: {oct(file_mode)} "
        f"(expected 0o600)"
    )


def test_final_file_permissions_fixed_when_initially_permissive(tmp_path) -> None:
    """Issue #5880: Final file should have 0o600 even if pre-existing file was permissive.

    This tests the scenario where:
    1. A file exists with permissive permissions (e.g., 0o644)
    2. save() is called
    3. The final file should now have 0o600 permissions

    This ensures explicit permission enforcement regardless of os.replace() behavior.
    """
    db = tmp_path / "todo.json"

    # Pre-create the file with permissive permissions (simulating a leaky umask)
    db.write_text("[]", encoding="utf-8")
    os.chmod(db, 0o644)  # rw-r--r--

    # Verify the file starts with permissive permissions
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o644, f"Setup failed: file should start as 0o644, got {oct(initial_mode)}"

    # Now save through TodoStorage
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="secret")])

    # Verify permissions are now restricted to 0o600
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final database file did not get restrictive permissions: {oct(file_mode)} "
        f"(expected 0o600). The file was initially 0o644 but save() should enforce 0o600."
    )


def test_final_file_no_group_or_other_access(tmp_path) -> None:
    """Issue #5880: Final file should not be readable by group or others.

    This is a security-focused test. The database file contains user data
    that should only be accessible by the owner.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="private data")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify group has no permissions
    assert not (file_mode & stat.S_IRGRP), f"Group can read file: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWGRP), f"Group can write file: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXGRP), f"Group can execute file: {oct(file_mode)}"

    # Verify others have no permissions
    assert not (file_mode & stat.S_IROTH), f"Others can read file: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWOTH), f"Others can write file: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXOTH), f"Others can execute file: {oct(file_mode)}"

"""Regression tests for issue #4722: Final file permissions should be explicit and secure.

Issue: After atomic rename (os.replace), the final target file permissions should be
verified to be secure (0o600). While the temp file gets secure permissions via os.fchmod,
the final file permissions should also be explicitly verified and documented.

Security concern: If an attacker creates a symlink or a pre-existing file with loose
permissions, the atomic replace could result in a file that doesn't have the expected
restrictive permissions. While os.replace preserves source file permissions (temp file),
explicit verification ensures defense-in-depth.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_secure_permissions(tmp_path) -> None:
    """Issue #4722: Final .todo.json file should have 0o600 permissions (rw-------).

    The save operation creates a temp file with 0o600, then uses os.replace()
    for atomic rename. We must verify the final file has secure permissions.

    Before fix: No explicit verification of final file permissions
    After fix: Final file is verified to have 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo list
    storage.save([Todo(id=1, text="test item")])

    # Verify the final file exists
    assert db.exists(), "Final .todo.json file should exist"

    # Verify the final file has secure permissions (0o600)
    file_stat = db.stat()
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


def test_final_file_permissions_after_update(tmp_path) -> None:
    """Issue #4722: Final file should have secure permissions after multiple saves.

    This tests the scenario where:
    1. First save creates the file
    2. Second save updates it

    The final file should maintain secure permissions across updates.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first item")])
    first_mode = stat.S_IMODE(db.stat().st_mode)
    assert first_mode == 0o600, f"First save: Expected 0o600, got {oct(first_mode)}"

    # Second save (update)
    storage.save([Todo(id=1, text="first item updated"), Todo(id=2, text="second item")])
    second_mode = stat.S_IMODE(db.stat().st_mode)
    assert second_mode == 0o600, f"Second save: Expected 0o600, got {oct(second_mode)}"


def test_final_file_permissions_after_overwrite_with_loose_perms(tmp_path) -> None:
    """Issue #4722: Final file should have secure permissions even if it previously had loose perms.

    This is the key security test:
    1. Create a file with overly permissive permissions (0o644)
    2. Save should result in a file with secure permissions (0o600)

    The os.replace() atomic rename preserves the source (temp file) permissions,
    which should result in secure final file.
    """
    db = tmp_path / "todo.json"

    # Pre-create the file with overly permissive permissions
    db.write_text('[]')
    os.chmod(db, 0o644)  # rw-r--r-- (loose permissions)

    # Verify pre-existing file has loose permissions
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o644, f"Setup failed: Expected 0o644, got {oct(initial_mode)}"

    # Now save through TodoStorage
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="test item")])

    # Verify the final file now has secure permissions
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == 0o600, (
        f"Final file should have secure permissions after overwrite. "
        f"Expected 0o600, got {oct(final_mode)}. "
        f"Pre-existing file had 0o644, save should have updated to 0o600."
    )

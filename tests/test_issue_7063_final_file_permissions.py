"""Regression tests for issue #7063: Final database file permissions should be 0o600.

Issue: The temp file is correctly secured with 0o600 permissions, but after
os.replace(), the final database file should also have restrictive permissions.

Security concern: If the final file has loose permissions, other users on the
system could read the todo database contents.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restrictive_permissions(tmp_path) -> None:
    """Issue #7063: Final database file should have 0o600 permissions (rw-------).

    After save() completes, the final database file should have restrictive
    permissions to prevent other users from reading the todo database.

    Before fix: Final file may have loose permissions (inherited from umask)
    After fix: Final file has 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo item
    storage.save([Todo(id=1, text="secret todo item")])

    # Verify final file exists
    assert db.exists(), "Final database file should exist"

    # Check permissions on the final file
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"File was: {db}"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, f"Final file has overly permissive mode: {oct(file_mode)}"


def test_final_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #7063: Final file permissions should remain 0o600 after overwriting.

    When saving to an existing file, the permissions should remain restrictive.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first todo")])

    # Verify initial permissions
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o600, f"Initial permissions should be 0o600, got {oct(initial_mode)}"

    # Second save (overwrite)
    storage.save([Todo(id=1, text="updated todo"), Todo(id=2, text="new todo")])

    # Verify permissions still restrictive after overwrite
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == 0o600, (
        f"Final file permissions should remain 0o600 after overwrite, "
        f"got {oct(final_mode)}"
    )


def test_final_file_no_execute_bit(tmp_path) -> None:
    """Issue #7063: Final database file should not have execute bit set.

    Data files should never be executable. This is a security best practice.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Check that no execute bits are set for anyone
    assert not (file_mode & stat.S_IXUSR), "Owner execute bit set on final file"
    assert not (file_mode & stat.S_IXGRP), "Group execute bit set on final file"
    assert not (file_mode & stat.S_IXOTH), "Other execute bit set on final file"

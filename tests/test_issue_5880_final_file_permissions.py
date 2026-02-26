"""Regression tests for issue #5880: Final database file permissions should be 0o600.

Issue: Temp file is created with 0o600 permissions, but after os.replace(),
the final file may not have restrictive permissions on some systems.

Security requirement: The final database file should have 0o600 (rw-------)
permissions to prevent unauthorized access to the data.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_database_file_has_restricted_permissions(tmp_path) -> None:
    """Issue #5880: Final database file should have 0o600 permissions (rw-------).

    The temp file is created with 0o600, but after os.replace(), we need to
    ensure the final file also has restricted permissions.

    Before fix: Final file may have default umask permissions (e.g., 0o644)
    After fix: Final file has 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo to create the database file
    storage.save([Todo(id=1, text="test todo")])

    # Check the final database file permissions
    assert db.exists(), "Database file should exist after save()"

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600). File: {db}"
    )

    # Specifically verify no execute bit is set
    assert not (file_mode & stat.S_IXUSR), (
        f"Final database file should not have owner execute bit set. "
        f"Mode: {oct(file_mode)}, File: {db}"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, f"Final file has overly permissive mode: {oct(file_mode)}"


def test_final_database_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #5880: Final database file permissions should stay 0o600 on subsequent saves.

    When the file already exists and is overwritten, permissions should remain 0o600.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first todo")])

    # Verify initial permissions
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o600, f"Initial permissions should be 0o600, got {oct(initial_mode)}"

    # Second save (overwrite)
    storage.save([Todo(id=1, text="updated todo"), Todo(id=2, text="second todo")])

    # Verify permissions are still 0o600
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == 0o600, (
        f"Final permissions should remain 0o600 after overwrite, got {oct(final_mode)}"
    )


def test_final_database_file_not_executable(tmp_path) -> None:
    """Issue #5880: Final database file should never be executable.

    This is a security-focused test. Data files should never be executable.
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

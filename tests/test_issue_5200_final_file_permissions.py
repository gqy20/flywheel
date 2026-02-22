"""Regression tests for issue #5200: Final database file permissions should be 0o600.

Issue: The temp file gets chmod 0o600, but after os.replace() the final file
may not preserve these restrictive permissions on all platforms.

The final .todo.json file must also have 0o600 permissions (rw-------) to
prevent unauthorized access to the todo data.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restricted_permissions(tmp_path) -> None:
    """Issue #5200: Final file should have exactly 0o600 permissions (rw-------).

    After os.replace() completes, the final database file should maintain
    the same restrictive permissions as the temp file.

    Before fix: Final file may have default permissions (often 0o644)
    After fix: Final file has 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo - this creates the final file via atomic replace
    storage.save([Todo(id=1, text="test")])

    # Check permissions on the FINAL file (not temp file)
    assert db.exists(), "Final database file should exist"
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final file has incorrect permissions: {oct(file_mode)} (expected 0o600). File was: {db}"
    )

    # Specifically verify no execute bit is set
    assert not (file_mode & stat.S_IXUSR), (
        f"Final file should not have owner execute bit set. Mode: {oct(file_mode)}, File: {db}"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, f"Final file has overly permissive mode: {oct(file_mode)}"


def test_final_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #5200: Overwriting existing file should also maintain 0o600.

    When overwriting an existing database file, the permissions should
    still be set correctly after the atomic replace.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - creates the file
    storage.save([Todo(id=1, text="initial")])

    # Verify first save has correct permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"After first save: expected 0o600, got {oct(file_mode)}"

    # Second save - overwrites the file
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])

    # Verify permissions are still correct after overwrite
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"After overwrite: expected 0o600, got {oct(file_mode)}"


def test_final_file_no_group_or_other_permissions(tmp_path) -> None:
    """Issue #5200: Final file should not allow group or other access.

    Security test: The database file should only be accessible by the owner.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="secret data")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # No group permissions
    assert not (file_mode & stat.S_IRGRP), f"Group read should not be set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWGRP), f"Group write should not be set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXGRP), f"Group execute should not be set: {oct(file_mode)}"

    # No other permissions
    assert not (file_mode & stat.S_IROTH), f"Other read should not be set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWOTH), f"Other write should not be set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXOTH), f"Other execute should not be set: {oct(file_mode)}"

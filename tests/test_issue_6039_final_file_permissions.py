"""Regression tests for issue #6039: Final file permissions not explicitly set.

Issue: After os.replace(temp_path, self.path), the final file should have
exactly 0o600 permissions. While os.replace may preserve permissions from the
temp file, this is not guaranteed on all platforms. We must explicitly set
permissions on the final file.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import stat

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


@pytest.fixture
def restrictive_umask():
    """Set a restrictive umask for testing.

    By default, umask is often 0o022 or 0o002, which wouldn't expose the bug
    since os.replace would preserve the 0o600 permissions. But with a more
    permissive umask (or on platforms where os.replace doesn't preserve perms),
    the final file could end up with different permissions.

    However, since we're testing the fix explicitly sets permissions,
    we can test directly after save() completes.
    """
    import os as os_module
    original_umask = os_module.umask(0o077)  # Restrictive umask
    yield
    os_module.umask(original_umask)


def test_final_file_has_0600_permissions(tmp_path) -> None:
    """Issue #6039: Final .todo.json file must have exactly 0o600 permissions.

    The fix must explicitly call os.chmod(self.path, 0o600) after os.replace()
    to ensure the final file has restrictive permissions, regardless of
    platform behavior or umask settings.

    Before fix: Final file may inherit umask or platform-specific permissions
    After fix: Final file always has 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test todo")])

    # Verify the final file exists
    assert db.exists(), f"Database file not created at {db}"

    # Get the final file's permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"File was: {db}"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify no execute bit for owner
    assert not (file_mode & stat.S_IXUSR), (
        f"Final file should not have owner execute bit set. "
        f"Mode: {oct(file_mode)}, File: {db}"
    )

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, (
        f"Final file has overly permissive mode: {oct(file_mode)}. "
        f"Group and others should have no access."
    )


def test_final_file_permissions_persist_across_multiple_saves(tmp_path) -> None:
    """Issue #6039: Final file permissions must be correct after multiple saves.

    Each save operation should ensure the final file has 0o600 permissions,
    even when overwriting an existing file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first todo")])
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"After first save: {oct(file_mode)}"

    # Second save (overwriting)
    storage.save([Todo(id=1, text="updated todo"), Todo(id=2, text="second todo")])
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"After second save: {oct(file_mode)}"

    # Third save
    storage.save([Todo(id=3, text="new todo")])
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"After third save: {oct(file_mode)}"


def test_final_file_group_and_others_have_no_access(tmp_path) -> None:
    """Issue #6039: Group and others must have no read/write/execute access.

    This is a security-critical test ensuring the todo file is only accessible
    by the owner.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="sensitive data")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Group permissions should be zero
    assert (file_mode & stat.S_IRGRP) == 0, f"Group should not have read: {oct(file_mode)}"
    assert (file_mode & stat.S_IWGRP) == 0, f"Group should not have write: {oct(file_mode)}"
    assert (file_mode & stat.S_IXGRP) == 0, f"Group should not have execute: {oct(file_mode)}"

    # Others permissions should be zero
    assert (file_mode & stat.S_IROTH) == 0, f"Others should not have read: {oct(file_mode)}"
    assert (file_mode & stat.S_IWOTH) == 0, f"Others should not have write: {oct(file_mode)}"
    assert (file_mode & stat.S_IXOTH) == 0, f"Others should not have execute: {oct(file_mode)}"

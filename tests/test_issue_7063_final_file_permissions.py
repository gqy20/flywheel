"""Regression tests for issue #7063: Final database file permissions must be 0o600.

Issue: Code sets temp file to 0o600 but os.replace() may not preserve permissions
on all platforms or when overwriting existing files. The final database file
must also have restricted permissions.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_database_file_has_restricted_permissions(tmp_path) -> None:
    """Issue #7063: Final database file should have 0o600 permissions (rw-------).

    The temp file is created with 0o600, but os.replace() may not preserve
    these permissions on all platforms. The final file must be explicitly
    set to 0o600 after the atomic rename.

    Before fix: Final file may have default umask permissions (e.g., 0o644)
    After fix: Final file has exactly 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo item
    storage.save([Todo(id=1, text="test item")])

    # Verify the final database file has exactly 0o600 permissions
    assert db.exists(), "Database file should exist after save"

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o})"
    )


def test_final_database_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #7063: Permissions should be 0o600 even when overwriting existing file.

    If a file already exists with looser permissions, overwriting it via
    os.replace() may inherit the old permissions. The fix must explicitly
    set 0o600 after each save.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file with loose permissions (simulating a pre-existing insecure file)
    db.write_text("[]", encoding="utf-8")
    os.chmod(db, 0o644)  # rw-r--r-- (insecure)

    # Verify initial state has loose permissions
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o644, f"Setup failed: initial mode is {oct(initial_mode)}"

    # Save should overwrite and set secure permissions
    storage.save([Todo(id=1, text="secure item")])

    # Verify the final file now has secure permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final database file should have 0o600 after overwriting insecure file, "
        f"but got {oct(file_mode)}"
    )


def test_final_database_file_not_readable_by_others(tmp_path) -> None:
    """Issue #7063: Final database file should not be readable by group/others.

    Security-focused test: the todo database may contain sensitive information
    and should only be readable by the owner.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="secret task")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify no group or other permissions
    assert not (file_mode & stat.S_IRGRP), f"File should not be group-readable: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWGRP), f"File should not be group-writable: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXGRP), f"File should not be group-executable: {oct(file_mode)}"
    assert not (file_mode & stat.S_IROTH), f"File should not be other-readable: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWOTH), f"File should not be other-writable: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXOTH), f"File should not be other-executable: {oct(file_mode)}"

    # Verify no execute bit for owner either (data file, not executable)
    assert not (file_mode & stat.S_IXUSR), f"File should not be executable: {oct(file_mode)}"

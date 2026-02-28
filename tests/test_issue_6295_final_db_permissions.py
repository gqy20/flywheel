"""Regression tests for issue #6295: Final db file should have 0o600 permissions.

Issue: After os.replace(temp_path, self.path), the final db file should have
restrictive 0o600 (rw-------) permissions, not just the temp file.

Security concern: If the final db file has overly permissive permissions (e.g.,
world-readable), sensitive todo data could be exposed to other users on the system.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_db_file_has_restrictive_permissions(tmp_path) -> None:
    """Issue #6295: Final db file should have exactly 0o600 permissions after save().

    The temp file is created with 0o600 permissions, and os.replace() should
    preserve those permissions. However, some filesystems or edge cases may
    affect final permissions, so we explicitly verify the final file has
    restrictive permissions.

    Before fix: Final file may have permissions inherited from umask
    After fix: Final file has exactly 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    storage.save([Todo(id=1, text="sensitive data")])

    # Verify the final db file exists
    assert db.exists(), "Final db file should exist after save()"

    # Get the file permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final db file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"File: {db}"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final db file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final db file lacks owner write: {oct(file_mode)}"

    # Verify no execute bit is set
    assert not (file_mode & stat.S_IXUSR), (
        f"Final db file should not have owner execute bit set. "
        f"Mode: {oct(file_mode)}, File: {db}"
    )

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, (
        f"Final db file has overly permissive mode: {oct(file_mode)}. "
        f"Group and others should have no access. File: {db}"
    )


def test_final_db_file_permissions_preserved_after_multiple_saves(tmp_path) -> None:
    """Issue #6295: Final db file permissions should remain 0o600 after multiple saves.

    Verifies that permissions are correctly set even when overwriting an existing file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first save")])
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"After first save: expected 0o600, got {oct(file_mode)}"

    # Second save (overwrites)
    storage.save([Todo(id=1, text="first"), Todo(id=2, text="second")])
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"After second save: expected 0o600, got {oct(file_mode)}"

    # Third save
    storage.save([Todo(id=3, text="third")])
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"After third save: expected 0o600, got {oct(file_mode)}"

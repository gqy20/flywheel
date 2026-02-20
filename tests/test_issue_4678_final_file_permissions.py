"""Regression tests for issue #4678: Final file inherits system umask.

Issue: After os.replace(), the final db file may not have restrictive permissions
because os.replace() preserves target permissions on some systems.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restrictive_permissions(tmp_path) -> None:
    """Issue #4678: Final db file should have mode 0o600 (owner read/write only).

    Before fix: os.replace() may preserve target permissions instead of source
    After fix: Final file should have restrictive permissions (0o600)

    Note: This test checks permissions AFTER save completes.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Verify final db file has restrictive permissions
    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Check that group and others have no permissions
    assert file_mode & 0o077 == 0, (
        f"Final file has overly permissive mode: {oct(file_mode)}. "
        f"Expected 0o600 (rw-------) or similar restrictive mode."
    )
    # Owner should have read+write at minimum
    assert file_mode & stat.S_IRUSR != 0, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR != 0, f"Final file lacks owner write: {oct(file_mode)}"


def test_final_file_permissions_after_overwrite(tmp_path) -> None:
    """Issue #4678: Final file permissions should remain restrictive after overwrite.

    If a file already exists with lax permissions, the new file should still
    get restrictive permissions after os.replace().
    """
    db = tmp_path / "todo.json"

    # Pre-create a file with overly permissive permissions
    db.write_text("[]", encoding="utf-8")
    os.chmod(db, 0o644)  # rw-r--r-- (overly permissive)

    # Verify initial permissions are too permissive
    initial_mode = stat.S_IMODE(os.stat(db).st_mode)
    assert initial_mode == 0o644, f"Pre-test setup failed: {oct(initial_mode)}"

    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # After save, permissions should be restrictive
    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode & 0o077 == 0, (
        f"Final file has overly permissive mode after overwrite: {oct(file_mode)}"
    )


def test_final_file_permissions_after_multiple_saves(tmp_path) -> None:
    """Issue #4678: Final file permissions should remain restrictive across multiple saves."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Do multiple saves
    for i in range(3):
        todos = [Todo(id=j, text=f"todo {j}") for j in range(i + 1)]
        storage.save(todos)

        # Check permissions after each save
        file_stat = os.stat(db)
        file_mode = stat.S_IMODE(file_stat.st_mode)

        assert file_mode & 0o077 == 0, (
            f"Final file has overly permissive mode on save {i}: {oct(file_mode)}"
        )


def test_final_file_permissions_when_replace_preserves_target(tmp_path) -> None:
    """Issue #4678: Final file should have restrictive permissions even when
    os.replace() would normally preserve target file permissions.

    This simulates behavior on systems where os.replace() preserves the
    permissions of the target file rather than the source.
    """
    db = tmp_path / "todo.json"

    # Pre-create a file with overly permissive permissions
    db.write_text("[]", encoding="utf-8")
    os.chmod(db, 0o644)  # rw-r--r-- (overly permissive)

    original_replace = os.replace

    def mock_replace(src, dst):
        """Mock os.replace that preserves target permissions (problematic behavior).

        Some systems preserve the target file's permissions rather than
        the source file's permissions when doing an atomic replace.
        """
        # Get the target's permissions before replace
        if os.path.exists(dst):
            target_mode = stat.S_IMODE(os.stat(dst).st_mode)
        else:
            target_mode = None

        # Do the actual replace
        result = original_replace(src, dst)

        # Simulate the problematic behavior: restore target permissions after replace
        # This mimics systems where os.replace doesn't carry over source permissions
        if target_mode is not None:
            os.chmod(dst, target_mode)

        return result

    # Patch os.replace inside the storage module to use our mock
    import flywheel.storage as storage_module
    with mock.patch.object(storage_module.os, "replace", side_effect=mock_replace):
        storage = TodoStorage(str(db))
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

    # After save, permissions should be restrictive (fix should call chmod after replace)
    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode & 0o077 == 0, (
        f"Final file has overly permissive mode: {oct(file_mode)}. "
        f"The fix should explicitly set permissions after os.replace()."
    )

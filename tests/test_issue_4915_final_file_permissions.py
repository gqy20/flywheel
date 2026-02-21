"""Regression tests for issue #4915: Final database file permissions should be 0o600.

Issue: No file permission enforcement on final database file after atomic rename.
The os.replace() call may not preserve the temp file's restrictive permissions
if the destination file already existed with different permissions.

Security Impact: Database files containing user data should not be world-readable.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_database_file_has_restrictive_permissions(tmp_path) -> None:
    """Issue #4915: Final database file should have exactly 0o600 permissions.

    After save() completes, the database file at self.path should have
    restrictive 0o600 (rw-------) permissions to prevent unauthorized access.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    storage.save([Todo(id=1, text="test")])

    # Verify the final database file has exactly 0o600 permissions
    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600). File: {db}"
    )


def test_final_database_permissions_after_overwrite(tmp_path) -> None:
    """Issue #4915: Final database file should be 0o600 even if it was 0o644 before.

    This is the critical security test. If a database file previously existed
    with permissive 0o644 (rw-r--r--) permissions, after save() it should be
    changed to restrictive 0o600 (rw-------) permissions.
    """
    db = tmp_path / "todo.json"

    # Create a file with permissive 0o644 permissions (world-readable)
    db.write_text('[]', encoding="utf-8")
    os.chmod(db, 0o644)

    # Verify the pre-existing file has 0o644 permissions
    initial_stat = os.stat(db)
    initial_mode = stat.S_IMODE(initial_stat.st_mode)
    assert initial_mode == 0o644, f"Setup failed: file has {oct(initial_mode)} not 0o644"

    # Now use TodoStorage to save new data
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="sensitive data")])

    # Verify the final database file now has 0o600 permissions
    final_stat = os.stat(db)
    final_mode = stat.S_IMODE(final_stat.st_mode)

    assert final_mode == 0o600, (
        f"Final database file has incorrect permissions after overwrite: {oct(final_mode)} "
        f"(expected 0o600). Previous permissions were 0o644. File: {db}"
    )


def test_multiple_saves_preserve_restrictive_permissions(tmp_path) -> None:
    """Issue #4915: Multiple saves should consistently maintain 0o600 permissions.

    Each save() operation should ensure the final file has 0o600 permissions,
    regardless of how many times the file is overwritten.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Perform multiple saves
    for i in range(3):
        storage.save([Todo(id=j, text=f"todo {j}") for j in range(i + 1)])

        # After each save, verify permissions
        file_stat = os.stat(db)
        file_mode = stat.S_IMODE(file_stat.st_mode)

        assert file_mode == 0o600, (
            f"After save #{i + 1}, database file has incorrect permissions: {oct(file_mode)} "
            f"(expected 0o600). File: {db}"
        )


def test_final_file_not_readable_by_group_or_others(tmp_path) -> None:
    """Issue #4915: Final database file should not be readable by group or others.

    Verify that after save(), the database file has no group or other permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="private data")])

    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify no group permissions
    assert not (file_mode & stat.S_IRGRP), f"Group read bit set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWGRP), f"Group write bit set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXGRP), f"Group execute bit set: {oct(file_mode)}"

    # Verify no other permissions
    assert not (file_mode & stat.S_IROTH), f"Other read bit set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWOTH), f"Other write bit set: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXOTH), f"Other execute bit set: {oct(file_mode)}"

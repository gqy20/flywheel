"""Regression tests for issue #3676: Original file permissions should be preserved after os.replace.

Issue: When TodoStorage.save() overwrites an existing file, os.replace() atomically moves
the temp file (with restrictive 0o600 permissions) to replace the target file. The resulting
file inherits the temp file's 0o600 permissions instead of preserving the original file's
permissions.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_preserves_original_file_permissions_on_overwrite(tmp_path) -> None:
    """Issue #3676: Original file permissions should be preserved when overwriting.

    Before fix: After overwrite, file has 0o600 (temp file permissions)
    After fix: After overwrite, file retains original permissions (e.g., 0o644)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file with specific permissions (rw-r--r--)
    storage.save([Todo(id=1, text="initial")])
    original_mode = stat.S_IMODE(db.stat().st_mode)

    # Change permissions to a different value to verify preservation
    # We use 0o644 (rw-r--r--) which is a common configuration file permission
    os.chmod(db, 0o644)
    expected_mode = 0o644

    # Verify permissions were set correctly
    actual_mode_before = stat.S_IMODE(db.stat().st_mode)
    assert actual_mode_before == expected_mode, (
        f"Failed to set test permissions: got {oct(actual_mode_before)}, "
        f"expected {oct(expected_mode)}"
    )

    # Overwrite the file
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])

    # Verify file content was updated correctly
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "updated"
    assert loaded[1].text == "new"

    # Verify original permissions were preserved
    actual_mode_after = stat.S_IMODE(db.stat().st_mode)
    assert actual_mode_after == expected_mode, (
        f"Original file permissions not preserved after overwrite. "
        f"Expected {oct(expected_mode)}, got {oct(actual_mode_after)}. "
        f"Original mode was {oct(original_mode)}."
    )


def test_new_file_has_restrictive_permissions(tmp_path) -> None:
    """Issue #3676: New files should still have secure default permissions (0o600).

    This verifies that the fix doesn't break the security requirement for new files.
    """
    db = tmp_path / "new_todo.json"
    storage = TodoStorage(str(db))

    # File should not exist yet
    assert not db.exists()

    # Create new file
    storage.save([Todo(id=1, text="first todo")])

    # Verify file was created
    assert db.exists()

    # New files should have restrictive permissions (0o600 - rw-------)
    actual_mode = stat.S_IMODE(db.stat().st_mode)
    assert actual_mode == 0o600, (
        f"New file should have restrictive 0o600 permissions, "
        f"got {oct(actual_mode)}"
    )


def test_preserves_owner_write_permission_on_overwrite(tmp_path) -> None:
    """Issue #3676: Verify specific permission bits are preserved.

    This test specifically checks that the owner write bit is preserved,
    which is critical for the user's ability to modify the file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file with specific permissions (rw-------)
    storage.save([Todo(id=1, text="initial")])
    os.chmod(db, 0o600)

    # Overwrite
    storage.save([Todo(id=1, text="updated")])

    # Verify owner can still read and write
    actual_mode = stat.S_IMODE(db.stat().st_mode)
    assert actual_mode & stat.S_IRUSR, "Owner should have read permission"
    assert actual_mode & stat.S_IWUSR, "Owner should have write permission"


def test_preserves_group_read_permission_on_overwrite(tmp_path) -> None:
    """Issue #3676: Verify group read permission is preserved when set.

    Some users may want group-readable todo files. This verifies those
    permissions are preserved.
    """
    db = tmp_path / "shared_todo.json"
    storage = TodoStorage(str(db))

    # Create file with group read permission (rw-r-----)
    storage.save([Todo(id=1, text="initial")])
    os.chmod(db, 0o640)

    # Overwrite
    storage.save([Todo(id=1, text="updated")])

    # Verify group read permission is preserved
    actual_mode = stat.S_IMODE(db.stat().st_mode)
    assert actual_mode == 0o640, (
        f"Group read permission not preserved. "
        f"Expected 0o640, got {oct(actual_mode)}"
    )

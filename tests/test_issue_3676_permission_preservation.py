"""Regression tests for issue #3676: Preserve original file permissions after atomic save.

Issue: When saving over an existing file, os.replace replaces the file atomically
but the resulting file has the temp file's permissions (0o600) instead of
preserving the original file's permissions.

Security implication: A file that was intentionally set with specific permissions
(e.g., 0o644 for shared read access) will unexpectedly become restrictive (0o600)
after a save operation, potentially breaking workflows that depend on the
original permissions.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_preserves_original_file_permissions_on_overwrite(tmp_path) -> None:
    """Issue #3676: Final file should preserve original file permissions after overwrite.

    When saving over an existing file:
    - Before fix: Final file has 0o600 (temp file perms)
    - After fix: Final file has original file's permissions preserved
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file with specific permissions (0o644 - rw-r--r--)
    original_permissions = 0o644
    storage.save([Todo(id=1, text="initial")])

    # Set specific permissions on the original file
    os.chmod(db, original_permissions)

    # Verify permissions were set
    original_mode = stat.S_IMODE(db.stat().st_mode)
    assert original_mode == original_permissions, (
        f"Failed to set initial permissions. Expected {oct(original_permissions)}, "
        f"got {oct(original_mode)}"
    )

    # Save again (overwrite)
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])

    # Verify final file permissions were preserved
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == original_permissions, (
        f"File permissions were not preserved after overwrite. "
        f"Expected {oct(original_permissions)}, got {oct(final_mode)}. "
        f"Temp file permissions (0o600) leaked into final file."
    )


def test_new_file_gets_default_restrictive_permissions(tmp_path) -> None:
    """Issue #3676: New files (not overwriting) should get restrictive 0o600 permissions.

    When saving to a new file that doesn't exist yet:
    - The temp file's 0o600 permissions should carry over to the final file
    - This is the expected behavior for new files
    """
    db = tmp_path / "new_todo.json"
    storage = TodoStorage(str(db))

    # Ensure file doesn't exist
    assert not db.exists()

    # Save to new file
    storage.save([Todo(id=1, text="first todo")])

    # New file should have restrictive permissions (from temp file)
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == 0o600, (
        f"New file should have 0o600 permissions, got {oct(final_mode)}"
    )


@pytest.mark.parametrize("original_perms", [0o644, 0o664, 0o666, 0o600])
def test_preserves_various_permission_modes(tmp_path, original_perms: int) -> None:
    """Issue #3676: Test preservation of various common permission modes.

    Tests that the fix works correctly for different common permission settings:
    - 0o644: Standard readable file (rw-r--r--)
    - 0o664: Group-writable file (rw-rw-r--)
    - 0o666: World-writable file (rw-rw-rw-)
    - 0o600: Private file (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Set specific permissions
    os.chmod(db, original_perms)

    # Overwrite
    storage.save([Todo(id=1, text="updated")])

    # Verify permissions preserved
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == original_perms, (
        f"Permissions not preserved for mode {oct(original_perms)}. "
        f"Got {oct(final_mode)}"
    )


def test_multiple_overwrites_preserve_permissions(tmp_path) -> None:
    """Issue #3676: Permissions should be preserved across multiple overwrites."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_permissions = 0o644

    # Create initial file with specific permissions
    storage.save([Todo(id=1, text="v1")])
    os.chmod(db, original_permissions)

    # Multiple overwrites
    for i in range(3):
        storage.save([Todo(id=1, text=f"v{i + 2}")])

        # Verify permissions still preserved after each overwrite
        final_mode = stat.S_IMODE(db.stat().st_mode)
        assert final_mode == original_permissions, (
            f"Permissions lost after overwrite #{i + 1}. "
            f"Expected {oct(original_permissions)}, got {oct(final_mode)}"
        )

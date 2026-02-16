"""Regression tests for issue #3676: File permissions not preserved after os.replace.

Issue: When overwriting an existing file, os.replace atomically moves the temp file
which has restrictive 0o600 permissions. The original file's permissions are lost.

Security impact: If a user intentionally set different permissions on their .todo.json
(e.g., 0o644 to allow group reads), those permissions would be silently changed to
0o600 on each save.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_preserve_original_file_permissions_on_overwrite(tmp_path) -> None:
    """Issue #3676: Original file permissions should be preserved after save.

    When a file already exists with custom permissions (e.g., 0o644),
    saving new content should preserve those permissions instead of
    replacing them with the temp file's restrictive 0o600 permissions.

    Before fix: After save, file has 0o600 (temp file perms)
    After fix: After save, file has 0o644 (original perms preserved)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Set custom permissions (e.g., group readable)
    # 0o644 = rw-r--r-- (owner read/write, group/others read)
    db.chmod(0o644)
    original_mode = stat.S_IMODE(db.stat().st_mode)
    assert original_mode == 0o644, f"Setup failed: expected 0o644, got {oct(original_mode)}"

    # Save new content - this should preserve the original permissions
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new item")])

    # Verify permissions were preserved
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == 0o644, (
        f"Permissions not preserved after save. "
        f"Expected: 0o644, Got: {oct(final_mode)}. "
        f"The temp file's 0o600 permissions replaced the original file's permissions."
    )


def test_new_file_gets_restrictive_permissions(tmp_path) -> None:
    """New files (no existing file to overwrite) should get restrictive 0o600.

    This verifies the security property for new files is maintained:
    - New files should be readable only by owner (0o600)
    - Existing files should preserve their permissions
    """
    db = tmp_path / "new_todo.json"
    storage = TodoStorage(str(db))

    # File doesn't exist yet
    assert not db.exists()

    # Create new file
    storage.save([Todo(id=1, text="new todo")])

    # New file should have restrictive permissions (0o600)
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == 0o600, (
        f"New file should have restrictive 0o600 permissions. "
        f"Got: {oct(final_mode)}"
    )


def test_preserve_custom_permissions_multiple_saves(tmp_path) -> None:
    """Issue #3676: Permissions should be preserved across multiple saves.

    This tests that the fix works consistently across multiple save operations.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file and set custom permissions
    storage.save([Todo(id=1, text="initial")])
    db.chmod(0o644)  # rw-r--r--

    # Multiple saves should all preserve permissions
    for i in range(3):
        storage.save([Todo(id=1, text=f"iteration-{i}")])
        final_mode = stat.S_IMODE(db.stat().st_mode)
        assert final_mode == 0o644, (
            f"Permissions lost on iteration {i}. "
            f"Expected: 0o644, Got: {oct(final_mode)}"
        )

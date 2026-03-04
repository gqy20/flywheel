"""Regression tests for issue #7217: Final file permissions should be 0o600 after atomic rename.

Issue: Final file permissions not set after atomic rename - only temp file has 0o600.

The os.replace() call preserves permissions but the final file may inherit
from previous version or default umask on some filesystems. We need to
explicitly set permissions on the final file after the atomic rename.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_0o600_permissions(tmp_path) -> None:
    """Issue #7217: Final db file should have exactly 0o600 permissions (rw-------).

    After os.replace(), the final file should have the same restrictive
    permissions as the temp file (0o600). This ensures consistent security
    regardless of filesystem behavior or pre-existing file permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # Verify final file has exactly 0o600 permissions
    assert db.exists(), "Final db file should exist"
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"File was: {db}"
    )


def test_final_file_permissions_after_overwrite(tmp_path) -> None:
    """Issue #7217: Final file should have 0o600 even when overwriting existing file.

    If a file already exists with different permissions, saving should
    result in the final file having 0o600 permissions.
    """
    db = tmp_path / "todo.json"

    # Create file with overly permissive permissions (0o644 - rw-r--r--)
    db.write_text("[]", encoding="utf-8")
    os.chmod(db, 0o644)

    # Verify initial permissions are different from 0o600
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o644, f"Setup failed: expected 0o644, got {oct(initial_mode)}"

    # Now save through TodoStorage
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="test")])

    # Verify final file has exactly 0o600 permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final file has incorrect permissions after overwrite: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"File was: {db}"
    )


def test_final_file_permissions_after_multiple_saves(tmp_path) -> None:
    """Issue #7217: Final file should maintain 0o600 after multiple saves.

    Each save operation should ensure the final file has correct permissions,
    even if something external modifies them between saves.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])
    mode1 = stat.S_IMODE(db.stat().st_mode)
    assert mode1 == 0o600, f"After first save: expected 0o600, got {oct(mode1)}"

    # Simulate external modification of permissions
    os.chmod(db, 0o666)  # Make it world-readable/writable
    mode_modified = stat.S_IMODE(db.stat().st_mode)
    assert mode_modified == 0o666, f"Setup failed: expected 0o666, got {oct(mode_modified)}"

    # Second save should restore correct permissions
    storage.save([Todo(id=1, text="first updated"), Todo(id=2, text="second")])
    mode2 = stat.S_IMODE(db.stat().st_mode)
    assert mode2 == 0o600, f"After second save: expected 0o600, got {oct(mode2)}"

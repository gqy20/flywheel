"""Regression tests for issue #7063: Final database file permissions should be 0o600.

Issue: After os.replace(), the final database file may not have restrictive permissions.
The code sets 0o600 on the temp file, but the final file created by first save
inherits umask, and subsequent saves may preserve existing file permissions.

Security: The final database file should have 0o600 permissions (rw-------) to prevent
other users from reading the todo database.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restricted_permissions(tmp_path) -> None:
    """Issue #7063: Final database file should have 0o600 permissions (rw-------).

    After save(), the final file at self.path should have restrictive permissions
    to prevent other users from reading the todo database.

    Before fix: Final file may have umask-based permissions (e.g., 0o644)
    After fix: Final file has 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # Verify final file exists
    assert db.exists(), "Final database file should exist"

    # Check final file permissions
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

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, f"Final file has overly permissive mode: {oct(file_mode)}"


def test_final_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #7063: Final file permissions should remain 0o600 after multiple saves.

    When overwriting an existing file, permissions should remain restrictive.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save creates the file
    storage.save([Todo(id=1, text="first")])
    first_mode = stat.S_IMODE(db.stat().st_mode)
    assert first_mode == 0o600, f"First save: expected 0o600, got {oct(first_mode)}"

    # Second save overwrites the file
    storage.save([Todo(id=2, text="second")])
    second_mode = stat.S_IMODE(db.stat().st_mode)
    assert second_mode == 0o600, f"Second save: expected 0o600, got {oct(second_mode)}"

    # Third save verifies consistency
    storage.save([Todo(id=3, text="third")])
    third_mode = stat.S_IMODE(db.stat().st_mode)
    assert third_mode == 0o600, f"Third save: expected 0o600, got {oct(third_mode)}"


def test_final_file_no_execute_bit(tmp_path) -> None:
    """Issue #7063: Final database file should not have execute bit set.

    This is a security-focused test. Data files should never be executable.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Check that no execute bits are set for anyone
    assert not (file_mode & stat.S_IXUSR), f"Owner execute bit set on {db}"
    assert not (file_mode & stat.S_IXGRP), f"Group execute bit set on {db}"
    assert not (file_mode & stat.S_IXOTH), f"Other execute bit set on {db}"

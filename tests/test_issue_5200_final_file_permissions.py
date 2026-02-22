"""Regression tests for issue #5200: Final database file permissions should be 0o600.

Issue: The temp file gets chmod 0o600, but os.replace() may not preserve permissions
on all platforms (behavior varies by OS/filesystem). The final .todo.json file must
have restrictive permissions guaranteed, not left to platform-dependent behavior.

Security: This ensures the final file always has 0o600, providing a consistent
security guarantee across all platforms.

This test documents the expected security behavior and verifies the explicit
chmod call after os.replace().
"""

from __future__ import annotations

import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restricted_permissions(tmp_path) -> None:
    """Issue #5200: Final database file should have exactly 0o600 permissions.

    After save(), the final .todo.json file must have restrictive permissions
    (0o600 = rw-------) to prevent unauthorized access.

    Before fix: Final file may have default umask permissions (e.g., 0o644)
    After fix: Final file has 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo to trigger the atomic write
    storage.save([Todo(id=1, text="test todo item")])

    # Verify the final file exists
    assert db.exists(), f"Database file {db} should exist after save"

    # Get the final file permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"File: {db}"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify no execute bit
    assert not (file_mode & stat.S_IXUSR), (
        f"Final file should not have owner execute bit set. "
        f"Mode: {oct(file_mode)}, File: {db}"
    )

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, (
        f"Final file has overly permissive mode for group/others: {oct(file_mode)}"
    )


def test_final_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #5200: Final file permissions should remain 0o600 after overwrite.

    When overwriting an existing file, the restrictive permissions should be
    maintained, not reset to umask defaults.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first save")])

    # Check first save permissions
    first_mode = stat.S_IMODE(db.stat().st_mode)
    assert first_mode == 0o600, f"First save should have 0o600, got {oct(first_mode)}"

    # Second save (overwrite)
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="second")])

    # Check permissions after overwrite
    second_mode = stat.S_IMODE(db.stat().st_mode)
    assert second_mode == 0o600, (
        f"After overwrite, permissions should remain 0o600, got {oct(second_mode)}"
    )


def test_final_file_not_readable_by_group_or_others(tmp_path) -> None:
    """Issue #5200: Final file should not be readable by group or others.

    Security-critical test: The database contains potentially sensitive todo items
    and should only be accessible by the owner.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="sensitive data")])

    file_mode = stat.S_IMODE(db.stat().st_mode)

    # Group should have no permissions
    assert not (file_mode & stat.S_IRGRP), f"Group should not read: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWGRP), f"Group should not write: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXGRP), f"Group should not execute: {oct(file_mode)}"

    # Others should have no permissions
    assert not (file_mode & stat.S_IROTH), f"Others should not read: {oct(file_mode)}"
    assert not (file_mode & stat.S_IWOTH), f"Others should not write: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXOTH), f"Others should not execute: {oct(file_mode)}"

"""Regression tests for issue #6039: Final file permissions not explicitly set.

Issue: Temp file gets restrictive 0o600 permissions via os.fchmod, but the final
file after os.replace may not reliably have these permissions. The final .todo.json
file must have exactly 0o600 permissions (rw-------) to protect sensitive data.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_0600_permissions(tmp_path) -> None:
    """Issue #6039: Final .todo.json file must have exactly 0o600 permissions.

    The temp file gets 0o600 via os.fchmod, but os.replace may not reliably
    preserve permissions on all platforms. We must explicitly set permissions
    on the final file to ensure security.

    Before fix: Final file permissions may vary based on umask/os.replace behavior
    After fix: Final file has exactly 0o600 (rw-------) - explicitly set
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    storage.save([Todo(id=1, text="test todo")])

    # Verify the FINAL file has exactly 0o600 permissions
    assert db.exists(), f"Final file should exist at {db}"

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"File: {db}"
    )

    # Specifically verify no execute bit is set
    assert not (file_mode & stat.S_IXUSR), (
        f"Final file should not have owner execute bit set. "
        f"Mode: {oct(file_mode)}, File: {db}"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, (
        f"Final file has overly permissive mode: {oct(file_mode)}. "
        f"Group and others should have no permissions."
    )


def test_final_file_permissions_after_overwrite(tmp_path) -> None:
    """Issue #6039: Permissions must be 0o600 even when overwriting existing file.

    If a file already exists with different permissions (e.g., 0o644), saving
    new todos should reset permissions to 0o600. On some platforms, os.replace
    may preserve permissions from the destination file rather than the source.
    The explicit os.chmod ensures consistent security.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file with permissive permissions
    db.write_text('[]', encoding='utf-8')
    os.chmod(db, 0o644)  # rw-r--r--

    # Verify initial permissions are NOT 0o600
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o644, f"Test setup failed: {oct(initial_mode)}"

    # Now save via TodoStorage
    storage.save([Todo(id=1, text="new todo")])

    # Verify final file has been corrected to 0o600
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == 0o600, (
        f"Final file should have 0o600 after overwrite, got {oct(final_mode)}"
    )


def test_final_file_permissions_with_permissive_umask(tmp_path, monkeypatch) -> None:
    """Issue #6039: Final file must be 0o600 even with permissive umask.

    This test simulates a scenario where a user has a very permissive umask (0o000).
    The final file must still have exactly 0o600 permissions regardless of umask.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save original umask and set very permissive one
    original_umask = os.umask(0o000)
    try:
        storage.save([Todo(id=1, text="test")])

        # Verify final file has exactly 0o600 despite permissive umask
        final_mode = stat.S_IMODE(db.stat().st_mode)
        assert final_mode == 0o600, (
            f"Final file should be 0o600 with permissive umask, got {oct(final_mode)}"
        )
    finally:
        os.umask(original_umask)


def test_final_file_group_others_no_access(tmp_path) -> None:
    """Issue #6039: Final file must not be readable by group or others.

    This is a security-focused test. The .todo.json file may contain
    sensitive data and should only be accessible by the owner.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="secret todo")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify group has no permissions
    assert not (file_mode & stat.S_IRGRP), "Group should not have read permission"
    assert not (file_mode & stat.S_IWGRP), "Group should not have write permission"
    assert not (file_mode & stat.S_IXGRP), "Group should not have execute permission"

    # Verify others have no permissions
    assert not (file_mode & stat.S_IROTH), "Others should not have read permission"
    assert not (file_mode & stat.S_IWOTH), "Others should not have write permission"
    assert not (file_mode & stat.S_IXOTH), "Others should not have execute permission"

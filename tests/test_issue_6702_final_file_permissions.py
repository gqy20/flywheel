"""Regression tests for issue #6702: Final database file permissions should be explicitly 0o600.

Issue: Final database file permissions are not set explicitly after atomic rename.

The temp file has 0o600 but the final file inherits previous permissions if it existed,
or uses umask defaults. This is a security issue because the final file should always
have consistent 0o600 permissions.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_0600_permissions_after_save(tmp_path) -> None:
    """Issue #6702: Final database file should have 0o600 permissions after save.

    After os.replace(), the final file should explicitly have 0o600 permissions
    to ensure consistent security posture.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # Verify final file has exactly 0o600 permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"File was: {db}"
    )


def test_final_file_permissions_corrected_when_preexisting_file_has_wrong_permissions(tmp_path) -> None:
    """Issue #6702: Permissions should be corrected even if file existed with wrong permissions.

    This test creates a file with overly permissive mode (0o666), then saves.
    The final file should be corrected to 0o600.

    While os.replace() typically preserves source permissions, there are edge cases
    (ACLs, different filesystems, NFS mounts) where this may not hold. Explicitly
    setting permissions ensures consistent security posture.
    """
    db = tmp_path / "todo.json"

    # Pre-create file with different (overly permissive) permissions
    # Use 0o666 to test that group/other bits are cleared
    db.write_text('[]', encoding='utf-8')
    os.chmod(db, 0o666)  # rw-rw-rw- - overly permissive

    # Verify pre-existing permissions
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o666, f"Setup failed: expected 0o666, got {oct(initial_mode)}"

    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="test")])

    # Verify final file permissions are corrected to 0o600
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final file permissions not corrected: {oct(file_mode)} "
        f"(expected 0o600). Pre-existing file had 0o666. "
        f"File was: {db}"
    )


def test_final_file_has_no_execute_bits(tmp_path) -> None:
    """Issue #6702: Final database file should not have any execute bits set.

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


def test_final_file_group_and_others_have_no_permissions(tmp_path) -> None:
    """Issue #6702: Final database file should not be accessible by group or others.

    Only owner should have read/write access (0o600 = rw-------).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, (
        f"Final file has overly permissive mode: {oct(file_mode)}. "
        f"Group and others should have no permissions."
    )

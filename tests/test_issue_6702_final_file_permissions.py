"""Regression tests for issue #6702: Final database file permissions should be explicitly set.

Issue: After atomic rename, the final database file should have explicit permissions
set to ensure consistent security posture (0o600), regardless of whether the file
existed before or what permissions it had.

The fix should explicitly chmod the final file after os.replace() to guarantee
consistent permissions, rather than relying on the temp file's permissions being
preserved.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_0600_permissions_after_save(tmp_path) -> None:
    """Issue #6702: Final database file should have exactly 0o600 permissions after save.

    The save() method should explicitly set permissions on the final file after
    the atomic rename to ensure consistent security posture.

    Before fix: Final file may have permissions from umask or previous file
    After fix: Final file explicitly set to 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save todos to a NEW file
    storage.save([Todo(id=1, text="test")])

    # Verify final file has exactly 0o600 permissions
    assert db.exists(), "Database file should exist after save"
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600). This is a security issue - the file should have "
        f"explicit permissions set after atomic rename."
    )


def test_final_file_permissions_corrected_after_overwrite(tmp_path) -> None:
    """Issue #6702: Overwriting existing file should correct permissions to 0o600.

    If a file exists with incorrect permissions, saving should correct them.
    This ensures consistent security even if the file was pre-created with
    loose permissions.
    """
    db = tmp_path / "todo.json"

    # Pre-create the file with overly permissive permissions (0o644 - rw-r--r--)
    db.write_text("[]", encoding="utf-8")
    os.chmod(db, 0o644)

    # Verify the file has incorrect permissions
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o644, f"Pre-condition failed: expected 0o644, got {oct(initial_mode)}"

    # Now save through TodoStorage
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="test")])

    # Verify final file has been corrected to 0o600
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions after overwrite: {oct(file_mode)} "
        f"(expected 0o600). The file had 0o644 before, save() should correct this."
    )


def test_final_file_permissions_no_group_or_other_access(tmp_path) -> None:
    """Issue #6702: Final file should have no group or other permissions.

    This is a security-focused test ensuring the database file is only
    accessible by the owner.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="secret data")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, (
        f"Final file has group or other permissions: {oct(file_mode)}. "
        f"Only owner should have access (0o600)."
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"

    # Verify no execute bit
    assert not (file_mode & stat.S_IXUSR), (
        f"Final file should not have owner execute bit. Mode: {oct(file_mode)}"
    )

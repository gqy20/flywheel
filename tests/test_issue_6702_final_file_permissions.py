"""Regression tests for issue #6702: Final database file permissions after atomic rename.

Issue: Final database file permissions are not set explicitly after atomic rename.
The temp file has 0o600 but the final file inherits previous permissions if it existed,
or uses umask defaults.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restricted_permissions(tmp_path) -> None:
    """Issue #6702: Final database file should have 0o600 permissions after save.

    After os.replace(), the final file should have consistent 0o600 (rw-------)
    permissions to ensure proper security posture.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # Verify final file has exactly 0o600 permissions
    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o})"
    )


def test_final_file_permissions_corrected_after_overwrite(tmp_path) -> None:
    """Issue #6702: Pre-existing file with wrong permissions should be corrected.

    If a file already exists with different permissions, after save it should
    have 0o600 permissions.
    """
    db = tmp_path / "todo.json"

    # Pre-create file with overly permissive permissions (0o644 - rw-r--r--)
    db.write_text("[]", encoding="utf-8")
    os.chmod(db, 0o644)

    # Verify initial permissions are wrong
    initial_stat = os.stat(db)
    initial_mode = stat.S_IMODE(initial_stat.st_mode)
    assert initial_mode == 0o644, f"Setup failed: initial mode is {oct(initial_mode)}"

    # Save should correct permissions to 0o600
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="test")])

    # Verify final file has 0o600 permissions
    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final file permissions not corrected: {oct(file_mode)} "
        f"(expected 0o600 after overwrite of file with 0o644)"
    )


def test_final_file_no_group_or_other_permissions(tmp_path) -> None:
    """Issue #6702: Final file should have no group or other permissions."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify group and others have no permissions
    assert (file_mode & 0o077) == 0, (
        f"Final file has group/other permissions: {oct(file_mode)}"
    )

    # Verify no execute bits are set
    assert not (file_mode & stat.S_IXUSR), "Final file has owner execute bit set"
    assert not (file_mode & stat.S_IXGRP), "Final file has group execute bit set"
    assert not (file_mode & stat.S_IXOTH), "Final file has other execute bit set"


def test_final_file_permissions_preserved_on_subsequent_save(tmp_path) -> None:
    """Issue #6702: Permissions should remain 0o600 on subsequent saves."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])

    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"First save: expected 0o600, got {oct(file_mode)}"

    # Second save (overwriting existing file)
    storage.save([Todo(id=1, text="first"), Todo(id=2, text="second")])

    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, f"Second save: expected 0o600, got {oct(file_mode)}"

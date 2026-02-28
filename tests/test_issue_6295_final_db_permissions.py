"""Regression tests for issue #6295: Final db file permissions should be 0o600.

Issue: The code creates a temp file with 0o600 permissions but os.replace()
may not preserve these permissions on the final file on all filesystems/umask settings.

Security Impact: If the final db file has permissive permissions (e.g., 0o644),
other users on the system could potentially read sensitive todo data.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_db_file_has_restrictive_permissions(tmp_path) -> None:
    """Issue #6295: Final db file should have 0o600 permissions (rw-------).

    The code creates a temp file with 0o600 permissions and uses os.replace()
    for atomic rename. However, os.replace() may not preserve permissions
    on all filesystems or under certain umask settings.

    Before fix: Final db file may inherit system umask permissions (e.g., 0o644)
    After fix: Final db file explicitly set to 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    storage.save([Todo(id=1, text="sensitive data")])

    # Check the final db file permissions
    assert db.exists(), "Final db file should exist"

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final db file has incorrect permissions: 0o{file_mode:o} "
        f"(expected 0o600). "
        f"File: {db}"
    )


def test_final_db_file_no_group_or_other_permissions(tmp_path) -> None:
    """Issue #6295: Final db file should not allow group/other access."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="private task")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify group and others have no permissions
    assert (file_mode & 0o077) == 0, (
        f"Final db file has group/other permissions: 0o{file_mode:o}. "
        f"Only owner should have access. File: {db}"
    )


def test_final_db_file_no_execute_permissions(tmp_path) -> None:
    """Issue #6295: Final db file should not be executable."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="data file")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Check that no execute bits are set for anyone
    assert not (file_mode & stat.S_IXUSR), f"Owner execute bit set on {db}"
    assert not (file_mode & stat.S_IXGRP), f"Group execute bit set on {db}"
    assert not (file_mode & stat.S_IXOTH), f"Other execute bit set on {db}"


def test_final_db_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #6295: Permissions should remain restrictive after overwriting."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initial save
    storage.save([Todo(id=1, text="first")])

    file_stat = db.stat()
    first_mode = stat.S_IMODE(file_stat.st_mode)
    assert first_mode == 0o600, f"Initial save: expected 0o600, got 0o{first_mode:o}"

    # Overwrite
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])

    file_stat = db.stat()
    second_mode = stat.S_IMODE(file_stat.st_mode)
    assert second_mode == 0o600, f"After overwrite: expected 0o600, got 0o{second_mode:o}"


def test_final_db_permissions_explicitly_set_after_replace(tmp_path) -> None:
    """Issue #6295: Code should explicitly chmod the final db file.

    This test verifies that the implementation explicitly sets permissions
    on the final file after os.replace(), rather than relying on
    os.replace() to preserve permissions from the temp file.

    This is important because:
    1. Some filesystems may not preserve permissions during replace
    2. The behavior may vary across platforms
    3. Explicit is better than implicit for security-critical operations
    """
    from unittest.mock import patch

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    chmod_calls = []

    def track_chmod(path, mode, *args, **kwargs):
        chmod_calls.append((str(path), mode))
        # Perform actual chmod
        return original_chmod(path, mode, *args, **kwargs)

    original_chmod = os.chmod

    with patch("flywheel.storage.os.chmod", side_effect=track_chmod):
        storage.save([Todo(id=1, text="test")])

    # Verify chmod was called on the final db file with 0o600
    db_chmod_calls = [(p, m) for p, m in chmod_calls if str(db) in p]
    assert len(db_chmod_calls) >= 1, (
        f"Expected os.chmod to be called on final db file. "
        f"chmod calls: {chmod_calls}"
    )

    # Verify the mode was 0o600
    _, mode = db_chmod_calls[-1]
    assert mode == 0o600, (
        f"Expected os.chmod to be called with 0o600, got 0o{mode:o}"
    )

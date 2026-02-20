"""Regression tests for issue #4722: Final target file permissions should be explicit.

Issue: After atomic rename, final .todo.json file should have explicit 0o600
permissions. While os.replace() preserves source file permissions, we should
explicitly set permissions after rename to ensure security and document behavior.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_explicit_0o600_permissions(tmp_path) -> None:
    """Issue #4722: Final file should have explicit 0o600 permissions after save.

    The save operation uses atomic rename (os.replace) which preserves temp file
    permissions. However, we should explicitly call os.chmod after rename to:
    1. Ensure final file has secure permissions regardless of edge cases
    2. Document the security intent clearly in code

    Before fix: Final file may inherit unexpected permissions from edge cases
    After fix: Final file always has 0o600 (rw-------)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test todo item")])

    # Verify final file exists
    assert db.exists(), "Final file should exist after save"

    # Check final file permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final file has incorrect permissions: 0o{file_mode:o} "
        f"(expected 0o600). File was: {db}"
    )

    # Specifically verify no execute bit is set
    assert not (file_mode & stat.S_IXUSR), (
        f"Final file should not have owner execute bit set. "
        f"Mode: 0o{file_mode:o}, File: {db}"
    )

    # Verify owner can read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: 0o{file_mode:o}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: 0o{file_mode:o}"

    # Verify group and others have no permissions
    assert file_mode & 0o077 == 0, f"Final file has overly permissive mode: 0o{file_mode:o}"


def test_preexisting_file_permissions_get_updated_to_0o600(tmp_path) -> None:
    """Issue #4722: Pre-existing file with loose perms should get secure perms after update.

    If a file already exists with loose permissions (e.g., 0o644), saving new
    content should update it to secure 0o600 permissions.
    """
    db = tmp_path / "todo.json"

    # Create file with intentionally loose permissions
    db.write_text('[]', encoding="utf-8")
    os.chmod(db, 0o644)  # rw-r--r--

    # Verify initial loose permissions
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o644, f"Setup failed: expected 0o644, got 0o{initial_mode:o}"

    # Now save through storage
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="updated content")])

    # Verify final file now has secure permissions
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == 0o600, (
        f"Final file should have secure permissions after update. "
        f"Got 0o{final_mode:o}, expected 0o600. File: {db}"
    )


def test_final_file_permissions_multiple_saves(tmp_path) -> None:
    """Issue #4722: Multiple saves should maintain secure permissions.

    Ensure that repeated saves don't accidentally change permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first save")])
    first_mode = stat.S_IMODE(db.stat().st_mode)
    assert first_mode == 0o600, f"First save: expected 0o600, got 0o{first_mode:o}"

    # Second save (update)
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])
    second_mode = stat.S_IMODE(db.stat().st_mode)
    assert second_mode == 0o600, f"Second save: expected 0o600, got 0o{second_mode:o}"

    # Third save (delete one)
    storage.save([Todo(id=2, text="only this one")])
    third_mode = stat.S_IMODE(db.stat().st_mode)
    assert third_mode == 0o600, f"Third save: expected 0o600, got 0o{third_mode:o}"

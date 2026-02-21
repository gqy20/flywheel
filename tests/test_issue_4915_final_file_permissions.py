"""Regression tests for issue #4915: Final database file permissions after atomic rename.

Issue: No file permission enforcement on final database file after atomic rename.

The temp file gets restrictive 0o600 permissions, but if the destination file
already exists with different permissions (e.g., 0o644), os.replace may not
change them. We need to explicitly enforce 0o600 on the final file.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_db_file_has_0o600_permissions(tmp_path) -> None:
    """Issue #4915: Final database file should have exactly 0o600 permissions.

    Scenario:
    1. Create a pre-existing database file with 0o644 (world-readable) permissions
    2. Call save() with new todos
    3. Verify final file has 0o600 (owner read/write only) permissions

    Before fix: Final file retains 0o644 permissions (security vulnerability)
    After fix: Final file has 0o600 permissions
    """
    db = tmp_path / "todo.json"

    # Pre-create the database file with overly permissive 0o644 permissions
    db.write_text("[]", encoding="utf-8")
    os.chmod(db, 0o644)

    # Verify pre-condition: file has 0o644 permissions
    initial_mode = stat.S_IMODE(db.stat().st_mode)
    assert initial_mode == 0o644, (
        f"Pre-condition failed: file should have 0o644, got {oct(initial_mode)}"
    )

    # Save new todos
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="test")])

    # Verify final file has exactly 0o600 permissions
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(final_mode)} "
        f"(expected 0o600, got 0o{final_mode:o}). "
        f"This is a security issue - the file may contain sensitive todo data."
    )


def test_final_db_file_permissions_on_new_file(tmp_path) -> None:
    """Issue #4915: New database file should also have 0o600 permissions.

    This tests the case where no file existed before.
    """
    db = tmp_path / "todo.json"

    # Verify no file exists
    assert not db.exists()

    # Save todos (creates new file)
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="test")])

    # Verify final file has exactly 0o600 permissions
    final_mode = stat.S_IMODE(db.stat().st_mode)
    assert final_mode == 0o600, (
        f"New database file has incorrect permissions: {oct(final_mode)} "
        f"(expected 0o600, got 0o{final_mode:o})"
    )


def test_final_db_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #4915: Permissions should be enforced even when overwriting existing file.

    Multiple saves should maintain 0o600 permissions.
    """
    db = tmp_path / "todo.json"

    # First save
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="first")])

    # Verify first save creates 0o600
    mode_after_first = stat.S_IMODE(db.stat().st_mode)
    assert mode_after_first == 0o600, f"First save should create 0o600, got {oct(mode_after_first)}"

    # Manually change permissions to 0o644 (simulating external modification)
    os.chmod(db, 0o644)

    # Second save
    storage.save([Todo(id=2, text="second")])

    # Verify second save enforces 0o600
    mode_after_second = stat.S_IMODE(db.stat().st_mode)
    assert mode_after_second == 0o600, (
        f"Second save should enforce 0o600, got {oct(mode_after_second)}"
    )

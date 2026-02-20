"""Regression tests for issue #4722: Final file permissions should be explicit.

Issue: After atomic rename, the final target file (.todo.json) permissions
should be verified to be restrictive (0o600). The current code sets temp file
to 0o600 and os.replace() preserves source permissions, but this behavior
is implicit and untested.

This test verifies that the FINAL file has secure permissions after save()
completes, not just the temp file.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restrictive_permissions(tmp_path) -> None:
    """Issue #4722: Final .todo.json should have 0o600 permissions after save.

    This test verifies the permissions of the FINAL target file, not the temp file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo list
    storage.save([Todo(id=1, text="test")])

    # Verify final file exists
    assert db.exists(), "Final file should exist"

    # Verify final file has exactly 0o600 permissions (rw-------)
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    assert file_mode == 0o600, (
        f"Final file has incorrect permissions: {oct(file_mode)} (expected 0o600). File was: {db}"
    )


def test_final_file_no_execute_bit(tmp_path) -> None:
    """Issue #4722: Final .todo.json should not have execute bit set."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify no execute bits are set
    assert not (file_mode & stat.S_IXUSR), f"Owner execute bit set on final file: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXGRP), f"Group execute bit set on final file: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXOTH), f"Other execute bit set on final file: {oct(file_mode)}"


def test_preexisting_loose_perms_replaced_with_restrictive(tmp_path) -> None:
    """Issue #4722: Pre-existing file with loose perms should get secure perms.

    If a .todo.json file already exists with loose permissions (e.g., 0o644),
    saving should update it to have restrictive permissions (0o600).
    """
    db = tmp_path / "todo.json"

    # Create a pre-existing file with loose permissions (world-readable)
    db.write_text("[]", encoding="utf-8")
    os.chmod(db, 0o644)  # rw-r--r--

    # Verify loose perms before save
    before_mode = stat.S_IMODE(db.stat().st_mode)
    assert before_mode == 0o644, (
        f"Setup failed: pre-existing file should have 0o644, got {oct(before_mode)}"
    )

    # Save new content
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="test")])

    # Verify final file now has restrictive permissions
    after_mode = stat.S_IMODE(db.stat().st_mode)
    assert after_mode == 0o600, (
        f"Final file should have 0o600 permissions, got {oct(after_mode)}. "
        f"Pre-existing loose permissions were not updated to restrictive."
    )


def test_permissions_preserved_on_subsequent_saves(tmp_path) -> None:
    """Issue #4722: Permissions should remain restrictive across multiple saves."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])
    first_mode = stat.S_IMODE(db.stat().st_mode)
    assert first_mode == 0o600, f"First save: expected 0o600, got {oct(first_mode)}"

    # Second save
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="second")])
    second_mode = stat.S_IMODE(db.stat().st_mode)
    assert second_mode == 0o600, f"Second save: expected 0o600, got {oct(second_mode)}"

    # Third save
    storage.save([Todo(id=3, text="third")])
    third_mode = stat.S_IMODE(db.stat().st_mode)
    assert third_mode == 0o600, f"Third save: expected 0o600, got {oct(third_mode)}"

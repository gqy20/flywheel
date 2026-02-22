"""Regression tests for issue #5151: Final file permissions verification.

Issue: The code sets restrictive permissions (0o600) on the temp file,
but there's no test to verify that the final file (after os.replace)
also has these restrictive permissions.

These tests verify the security of the final JSON file permissions.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restrictive_permissions(tmp_path) -> None:
    """Issue #5151: Final JSON file should have mode 0o600 (owner read/write only).

    After save(), the final file should inherit the temp file's restrictive
    permissions (0o600) through os.replace.

    Before fix: No test verifies final file permissions
    After fix: This test verifies final file has restrictive permissions
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Verify the final file exists
    assert db.exists(), "Final JSON file should exist after save()"

    # Verify the final file has restrictive permissions (0o600)
    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Check that group and others have no permissions
    assert file_mode & 0o077 == 0, (
        f"Final file has overly permissive mode: {oct(file_mode)}. "
        f"Expected 0o600 (rw-------) or more restrictive."
    )

    # Owner should have read+write
    assert file_mode & stat.S_IRUSR != 0, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR != 0, f"Final file lacks owner write: {oct(file_mode)}"


def test_final_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #5151: Final file permissions should be preserved when overwriting.

    When overwriting an existing file, the new file should still have
    restrictive permissions (0o600), not the permissions of any pre-existing file.
    """
    db = tmp_path / "todo.json"

    # Create initial file with permissive permissions (simulating an insecure pre-existing file)
    db.write_text("[]", encoding="utf-8")
    os.chmod(db, 0o644)  # rw-r--r-- (insecure)

    # Verify initial permissions are permissive
    initial_mode = stat.S_IMODE(os.stat(db).st_mode)
    assert initial_mode & 0o044 != 0, "Test setup: initial file should be world-readable"

    # Now use TodoStorage to save (should apply restrictive permissions)
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="secure todo")])

    # Verify final file has restrictive permissions
    final_mode = stat.S_IMODE(os.stat(db).st_mode)
    assert final_mode & 0o077 == 0, (
        f"Final file should not have group/other permissions: {oct(final_mode)}"
    )


def test_final_file_permissions_match_temp_file_permissions(tmp_path) -> None:
    """Issue #5151: Final file should have same restrictive permissions as temp file.

    This ensures consistency between temp file security (verified in issue #1999 tests)
    and final file security.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save todos
    storage.save([Todo(id=1, text="test")])

    # Get final file permissions
    final_stat = os.stat(db)
    final_mode = stat.S_IMODE(final_stat.st_mode)

    # The final file should have exactly 0o600 permissions
    # (matching what was set on the temp file via os.fchmod)
    expected_mode = stat.S_IRUSR | stat.S_IWUSR  # 0o600

    assert final_mode == expected_mode, (
        f"Final file mode {oct(final_mode)} does not match expected {oct(expected_mode)}"
    )

"""Regression tests for issue #6039: Final file permissions not explicitly set.

Issue: Only temp file gets restrictive permissions (0o600 via os.fchmod),
but after os.replace, the final file may inherit umask or retain original
file's permissions instead of having explicitly set 0o600.

The final .todo.json file should have exactly 0o600 permissions (rw-------).

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_restricted_permissions(tmp_path) -> None:
    """Issue #6039: Final .todo.json file should have exactly 0o600 permissions.

    After os.replace(), the final file should have explicitly set 0o600 (rw-------)
    permissions, not inheriting from umask or the original temp file.

    Before fix: Final file inherits umask or retains original permissions
    After fix: Final file has explicitly set 0o600 permissions
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save a todo item
    storage.save([Todo(id=1, text="test")])

    # Verify the final file exists
    assert db.exists(), f"Final file {db} was not created"

    # Get the final file's permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be EXACTLY 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"Final file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600, got 0o{file_mode:o}). "
        f"File: {db}"
    )


def test_final_file_no_group_or_other_permissions(tmp_path) -> None:
    """Issue #6039: Final file should not allow group or others access.

    This is a security-focused test. The todo file may contain sensitive
    information and should only be accessible by the owner.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="secret task")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify group and others have no permissions (mask 0o077)
    group_other_mask = file_mode & 0o077
    assert group_other_mask == 0, (
        f"Final file has group/other permissions: {oct(file_mode)} "
        f"(should be 0o600). File: {db}"
    )


def test_final_file_no_execute_permissions(tmp_path) -> None:
    """Issue #6039: Final file should not be executable.

    Data files should never have execute permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="data task")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Check that no execute bits are set for anyone
    assert not (file_mode & stat.S_IXUSR), f"Owner execute bit set on final file {db}"
    assert not (file_mode & stat.S_IXGRP), f"Group execute bit set on final file {db}"
    assert not (file_mode & stat.S_IXOTH), f"Other execute bit set on final file {db}"


def test_final_file_permissions_preserved_on_overwrite(tmp_path) -> None:
    """Issue #6039: Final file should retain 0o600 permissions on subsequent saves.

    When a file already exists and is overwritten, the new file should
    still have 0o600 permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])

    # Check permissions after first save
    first_stat = db.stat()
    first_mode = stat.S_IMODE(first_stat.st_mode)
    assert first_mode == 0o600, f"First save: expected 0o600, got {oct(first_mode)}"

    # Second save (overwrite)
    storage.save([Todo(id=1, text="first updated"), Todo(id=2, text="second")])

    # Check permissions after second save
    second_stat = db.stat()
    second_mode = stat.S_IMODE(second_stat.st_mode)
    assert second_mode == 0o600, f"Second save: expected 0o600, got {oct(second_mode)}"

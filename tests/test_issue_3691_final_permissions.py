"""Regression tests for issue #3691: Final file permissions after atomic rename.

Issue: save() creates temp file with 0o600 permissions, then uses os.replace()
which preserves those permissions on the final file. The final file should have
standard readable permissions (0o644) instead of restrictive 0o600.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_readable_permissions(tmp_path) -> None:
    """Issue #3691: Final file should have 0o644 permissions (rw-r--r--).

    The temp file correctly uses 0o600 (rw-------) for security during write,
    but after atomic rename, the final file should have standard readable
    permissions so other users/tools can read the todo database.

    Before fix: Final file has 0o600 (rw-------) - inherited from temp file
    After fix: Final file has 0o644 (rw-r--r--) - standard readable permissions
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    storage.save([Todo(id=1, text="test")])

    # Verify final file exists
    assert db.exists(), "Final file should exist after save()"

    # Get final file permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be 0o644 (rw-r--r--)
    # - Owner can read and write
    # - Group can read
    # - Others can read
    expected_mode = 0o644  # rw-r--r--

    assert file_mode == expected_mode, (
        f"Final file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o644, got 0o{file_mode:o}). "
        f"File was: {db}"
    )


def test_final_file_permissions_owner_readable_writable(tmp_path) -> None:
    """Issue #3691: Final file owner permissions should be rw-."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Owner should be able to read and write
    assert file_mode & stat.S_IRUSR, f"Final file lacks owner read: {oct(file_mode)}"
    assert file_mode & stat.S_IWUSR, f"Final file lacks owner write: {oct(file_mode)}"
    # Owner should NOT have execute
    assert not (file_mode & stat.S_IXUSR), f"Final file should not have owner execute: {oct(file_mode)}"


def test_final_file_permissions_group_readable(tmp_path) -> None:
    """Issue #3691: Final file group permissions should be r--."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Group should be able to read
    assert file_mode & stat.S_IRGRP, f"Final file lacks group read: {oct(file_mode)}"
    # Group should NOT have write or execute
    assert not (file_mode & stat.S_IWGRP), f"Final file should not have group write: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXGRP), f"Final file should not have group execute: {oct(file_mode)}"


def test_final_file_permissions_others_readable(tmp_path) -> None:
    """Issue #3691: Final file others permissions should be r--."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Others should be able to read
    assert file_mode & stat.S_IROTH, f"Final file lacks others read: {oct(file_mode)}"
    # Others should NOT have write or execute
    assert not (file_mode & stat.S_IWOTH), f"Final file should not have others write: {oct(file_mode)}"
    assert not (file_mode & stat.S_IXOTH), f"Final file should not have others execute: {oct(file_mode)}"


def test_final_file_permissions_consistent_across_saves(tmp_path) -> None:
    """Issue #3691: Final file permissions should be consistent across multiple saves."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])
    first_mode = stat.S_IMODE(db.stat().st_mode)

    # Second save (overwrite)
    storage.save([Todo(id=1, text="second"), Todo(id=2, text="added")])
    second_mode = stat.S_IMODE(db.stat().st_mode)

    # Third save
    storage.save([Todo(id=3, text="third")])
    third_mode = stat.S_IMODE(db.stat().st_mode)

    # All should have the same expected permissions
    expected_mode = 0o644
    assert first_mode == expected_mode, f"First save: expected 0o644, got 0o{first_mode:o}"
    assert second_mode == expected_mode, f"Second save: expected 0o644, got 0o{second_mode:o}"
    assert third_mode == expected_mode, f"Third save: expected 0o644, got 0o{third_mode:o}"


def test_temp_file_still_has_restrictive_permissions(tmp_path) -> None:
    """Issue #3691: Temp file should still have 0o600 during write (security).

    This test ensures that while we fix final file permissions, we don't
    accidentally change the temp file permissions which are intentionally
    restrictive for security.
    """
    import tempfile as tempfile_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track permissions of created temp files
    permissions_seen = []

    original_mkstemp = tempfile_module.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        # Check permissions immediately after creation
        file_stat = os.stat(path)
        file_mode = stat.S_IMODE(file_stat.st_mode)
        permissions_seen.append((path, file_mode))
        return fd, path

    import tempfile
    original = tempfile.mkstemp
    tempfile.mkstemp = tracking_mkstemp

    try:
        storage.save([Todo(id=1, text="test")])
    finally:
        tempfile.mkstemp = original

    # Verify temp file was created with 0o600 permissions (unchanged from before)
    assert len(permissions_seen) > 0, "No temp files were created"

    for path, mode in permissions_seen:
        assert mode == 0o600, (
            f"Temp file should have 0o600 permissions, got 0o{mode:o}. "
            f"File was: {path}"
        )

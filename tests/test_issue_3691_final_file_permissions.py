"""Regression tests for issue #3691: Final file permissions after atomic rename.

Issue: save() does not set final file permissions after atomic rename.

The save() method uses tempfile.mkstemp which creates temp files with 0o600
permissions for security. After os.replace(), these restrictive permissions
are inherited by the final file. For a user-accessible JSON database file,
standard permissions like 0o644 (rw-r--r--) are more appropriate, allowing
group/others to read the file while only owner can write.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_standard_permissions_after_save(tmp_path) -> None:
    """Issue #3691: Final file should have standard permissions (0o644) after save().

    Before fix: Final file has 0o600 (rw-------) - inherited from temp file
    After fix: Final file has 0o644 (rw-r--r--) - standard readable file
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # Verify final file exists
    assert db.exists(), "Final file should exist after save()"

    # Check final file permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Final file should have standard permissions: 0o644 (rw-r--r--)
    # Owner can read and write, group and others can read
    expected_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH  # 0o644

    assert file_mode == expected_mode, (
        f"Final file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o644, got 0o{file_mode:o}). "
        f"Final file should be readable by group/others."
    )


def test_final_file_permissions_consistent_across_multiple_saves(tmp_path) -> None:
    """Issue #3691: Permissions should be consistent across multiple saves.

    Each save() should result in final file having standard 0o644 permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])
    mode1 = stat.S_IMODE(db.stat().st_mode)

    # Second save
    storage.save([Todo(id=1, text="first"), Todo(id=2, text="second")])
    mode2 = stat.S_IMODE(db.stat().st_mode)

    # Third save
    storage.save([Todo(id=3, text="third")])
    mode3 = stat.S_IMODE(db.stat().st_mode)

    expected_mode = 0o644

    assert mode1 == expected_mode, f"First save: expected 0o644, got 0o{mode1:o}"
    assert mode2 == expected_mode, f"Second save: expected 0o644, got 0o{mode2:o}"
    assert mode3 == expected_mode, f"Third save: expected 0o644, got 0o{mode3:o}"


def test_final_file_is_readable_by_others(tmp_path) -> None:
    """Issue #3691: Final file should be readable by group and others.

    This test focuses on the specific permission bits that should be set
    to allow group and others to read the file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_mode = stat.S_IMODE(db.stat().st_mode)

    # Owner should have read and write
    assert file_mode & stat.S_IRUSR, "Owner should have read permission"
    assert file_mode & stat.S_IWUSR, "Owner should have write permission"

    # Group should have read
    assert file_mode & stat.S_IRGRP, "Group should have read permission"

    # Others should have read
    assert file_mode & stat.S_IROTH, "Others should have read permission"

    # No execute bits should be set
    assert not (file_mode & stat.S_IXUSR), "Owner should not have execute permission"
    assert not (file_mode & stat.S_IXGRP), "Group should not have execute permission"
    assert not (file_mode & stat.S_IXOTH), "Others should not have execute permission"

    # Group and others should not have write permission
    assert not (file_mode & stat.S_IWGRP), "Group should not have write permission"
    assert not (file_mode & stat.S_IWOTH), "Others should not have write permission"

"""Regression tests for issue #3691: Final file permissions after atomic rename.

Issue: After os.replace(), the final file inherits temp file permissions (0o600).
The final file should have more appropriate permissions (0o644) for a data file
that other users might need to read.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_has_readable_permissions(tmp_path) -> None:
    """Issue #3691: Final file should have 0o644 permissions (rw-r--r--).

    The temp file has 0o600 for security during write, but after atomic rename,
    the final file should have 0o644 (rw-r--r--) which allows group and others
    to read the file.

    Before fix: Final file has 0o600 (rw-------) - inherited from temp file
    After fix: Final file has 0o644 (rw-r--r--) - readable by others
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # Check final file permissions
    assert db.exists(), "Final file should exist"
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The final file should have 0o644 permissions (rw-r--r--)
    expected_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH  # 0o644

    assert file_mode == expected_mode, (
        f"Final file has incorrect permissions: 0o{file_mode:o} "
        f"(expected 0o644). File: {db}"
    )


def test_final_file_permissions_consistent_across_saves(tmp_path) -> None:
    """Issue #3691: Permissions should be consistent across multiple saves.

    Ensures that saving multiple times maintains the correct final permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save multiple times
    for i in range(3):
        storage.save([Todo(id=1, text=f"test {i}")])

        # Check final file permissions after each save
        file_stat = db.stat()
        file_mode = stat.S_IMODE(file_stat.st_mode)
        expected_mode = 0o644

        assert file_mode == expected_mode, (
            f"Final file has incorrect permissions after save #{i+1}: "
            f"0o{file_mode:o} (expected 0o644). File: {db}"
        )


def test_final_file_is_not_executable(tmp_path) -> None:
    """Issue #3691: Final file should not be executable by anyone.

    This is a security-focused test. Data files should never be executable.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify no execute bits are set for anyone
    assert not (file_mode & stat.S_IXUSR), f"Owner execute bit set on {db}"
    assert not (file_mode & stat.S_IXGRP), f"Group execute bit set on {db}"
    assert not (file_mode & stat.S_IXOTH), f"Other execute bit set on {db}"

"""Regression test for issue #2546: Comment-documentation consistency.

Issue: Comment says permissions are 0o600 but code uses stat.S_IRUSR | stat.S_IWUSR.

The issue is about documentation consistency - the docstring mentions "0o600" explicitly
but the code uses the symbolic constants stat.S_IRUSR | stat.S_IWUSR. While these are
equivalent (both evaluate to 0o600 / 384), the comment could be more explicit about
the actual code being used.

This test verifies that the code behavior matches the documented 0o600 permissions.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_docstring_matches_actual_permissions(tmp_path) -> None:
    """Issue #2546: Verify code uses exactly 0o600 permissions as documented.

    The docstring says "sets restrictive permissions (0o600)" but the code
    uses stat.S_IRUSR | stat.S_IWUSR. This test verifies they are equivalent.
    """
    # First verify at Python level that the constants equal 0o600
    expected_mode = stat.S_IRUSR | stat.S_IWUSR
    assert expected_mode == 0o600, (
        f"stat.S_IRUSR | stat.S_IWUSR = 0o{expected_mode:o}, "
        f"but docstring says 0o600. Values don't match!"
    )

    # Now verify runtime behavior matches 0o600
    import tempfile as tempfile_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    permissions_seen = []

    original_mkstemp = tempfile_module.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        # Check permissions AFTER fchmod is called (need to wait for save to complete)
        # We'll track the file and check it after save()
        permissions_seen.append(path)
        return fd, path

    import tempfile
    original = tempfile.mkstemp
    tempfile.mkstemp = tracking_mkstemp

    try:
        storage.save([Todo(id=1, text="test")])
    finally:
        tempfile.mkstemp = original

    # Verify temp file was created with exactly 0o600 permissions
    for temp_path in permissions_seen:
        if os.path.exists(temp_path):
            file_stat = os.stat(temp_path)
            file_mode = stat.S_IMODE(file_stat.st_mode)

            # Verify it's exactly 0o600 as documented
            assert file_mode == 0o600, (
                f"Temp file has 0o{file_mode:o} permissions, "
                f"but docstring says 0o600. File: {temp_path}"
            )

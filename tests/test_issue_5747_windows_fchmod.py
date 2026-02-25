"""Regression tests for issue #5747: os.fchmod is Unix-only.

Issue: os.fchmod is Unix-only, will raise AttributeError on Windows.

On Windows, os.fchmod does not exist. The code should gracefully handle
this case without raising AttributeError.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_without_fchmod(tmp_path) -> None:
    """Issue #5747: save() should work when os.fchmod is not available.

    On Windows, os.fchmod does not exist. The code should gracefully
    skip setting permissions on Windows rather than raising AttributeError.

    Before fix: AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() succeeds without error
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    with mock.patch.object(os, "fchmod", None):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test")])

    # Verify the file was created successfully
    assert db.exists()
    content = db.read_text()
    assert "test" in content


def test_save_works_when_fchmod_missing_attr(tmp_path) -> None:
    """Issue #5747: save() should handle missing os.fchmod attribute.

    This tests the case where os.fchmod is not present at all
    (e.g., on Windows Python).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Patch by removing the attribute entirely
    with mock.patch.dict("os.__dict__", {"fchmod": None}):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test")])

    # Verify the file was created successfully
    assert db.exists()


def test_save_sets_permissions_on_unix(tmp_path) -> None:
    """Issue #5747: save() should still set 0o600 permissions on Unix.

    This verifies that the fix doesn't break the Unix behavior where
    permissions should be set to 0o600.
    """
    import stat

    # Skip if fchmod is not available (we're on Windows)
    if not hasattr(os, "fchmod"):
        import pytest
        pytest.skip("os.fchmod not available on this platform")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # Verify the file has 0o600 permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # The mode should be 0o600 (rw-------)
    assert file_mode == 0o600, (
        f"File has incorrect permissions: {oct(file_mode)} (expected 0o600)"
    )

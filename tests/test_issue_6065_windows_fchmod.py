"""Regression tests for issue #6065: os.fchmod is Unix-only and will raise AttributeError on Windows.

Issue: os.fchmod is not available on Windows and will raise AttributeError when called.

The code should handle Windows gracefully by either:
1. Using hasattr check before calling os.fchmod
2. Wrapping in try/except AttributeError

This test FAILS before the fix (simulates Windows behavior) and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest import mock

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Issue #6065: save() should handle missing os.fchmod on Windows.

    On Windows, os.fchmod does not exist. The code should handle this
    gracefully without raising AttributeError.

    This test simulates Windows behavior by hiding os.fchmod.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by hiding os.fchmod
    with mock.patch.object(os, "fchmod", None, create=False):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test")])

    # Verify the file was saved correctly
    assert db.exists()
    content = db.read_text()
    assert '"text": "test"' in content


def test_save_handles_attribute_error_on_fchmod(tmp_path) -> None:
    """Issue #6065: save() should catch AttributeError when os.fchmod fails.

    Even if os.fchmod exists but raises AttributeError (edge case),
    the save operation should still complete.
    """

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    def mock_fchmod(*args, **kwargs):
        raise AttributeError("mocked fchmod not available")

    with mock.patch.object(os, "fchmod", mock_fchmod):
        # This should NOT raise AttributeError - it should be caught
        storage.save([Todo(id=1, text="test")])

    # Verify the file was saved correctly despite fchmod failure
    assert db.exists()


@pytest.mark.skipif(not hasattr(os, "fchmod"), reason="os.fchmod not available on this platform")
def test_save_still_sets_permissions_on_unix(tmp_path) -> None:
    """Issue #6065: On Unix, save() should still set 0o600 permissions.

    This test ensures that the Windows compatibility fix doesn't break
    the intended security behavior on Unix systems.
    """
    import tempfile

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    temp_files_created = []

    original_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(path)
        return fd, path

    with mock.patch("tempfile.mkstemp", tracking_mkstemp):
        storage.save([Todo(id=1, text="test")])

    # Check that temp file had restrictive permissions set
    # Note: We check the temp file, not the final file (which inherits umask)
    for temp_path in temp_files_created:
        if Path(temp_path).exists():
            file_stat = os.stat(temp_path)
            file_mode = stat.S_IMODE(file_stat.st_mode)
            # On Unix, permissions should be exactly 0o600
            assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"

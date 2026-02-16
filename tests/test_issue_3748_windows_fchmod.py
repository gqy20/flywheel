"""Regression tests for issue #3748: os.fchmod unavailable on Windows.

Issue: os.fchmod is not available on Windows, causing save() to crash
with AttributeError on Windows platform.

The fix should gracefully handle the absence of os.fchmod on Windows
by catching the AttributeError and continuing with the save operation.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Issue #3748: save() should work when os.fchmod is not available.

    On Windows, os.fchmod does not exist. The code should handle this
    gracefully by catching the AttributeError and continuing with the
    save operation.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows behavior where os.fchmod does not exist
    with mock.patch.object(
        os,
        "fchmod",
        create=True,
        side_effect=AttributeError("module 'os' has no attribute 'fchmod'"),
    ):
        # This should NOT raise an exception
        storage.save([Todo(id=1, text="test")])

    # Verify the file was saved correctly
    assert db.exists()
    content = db.read_text()
    assert '"text": "test"' in content


def test_save_continues_when_fchmod_raises_oserror(tmp_path) -> None:
    """Issue #3748: save() should handle OSError from os.fchmod gracefully.

    Even on platforms where os.fchmod exists, it might fail for various
    reasons (e.g., special filesystems). The code should handle this.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate OSError from os.fchmod (e.g., on special filesystems)
    with mock.patch.object(os, "fchmod", side_effect=OSError("Operation not supported")):
        # This should NOT raise an exception
        storage.save([Todo(id=1, text="test")])

    # Verify the file was saved correctly
    assert db.exists()
    content = db.read_text()
    assert '"text": "test"' in content


@pytest.mark.skipif(sys.platform == "win32", reason="Permission test only valid on Unix")
def test_fchmod_still_called_on_unix(tmp_path) -> None:
    """Issue #3748: os.fchmod should still be called on Unix platforms.

    On Unix platforms, os.fchmod should be called to set proper permissions.
    This test verifies the fix doesn't break Unix permission handling.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock fchmod to track if it's called
    with mock.patch.object(os, "fchmod", wraps=os.fchmod) as mock_fchmod:
        storage.save([Todo(id=1, text="test")])

        # Verify fchmod was called
        mock_fchmod.assert_called_once()
        # Verify it was called with the correct mode (0o600)
        args, _ = mock_fchmod.call_args
        assert args[1] == 0o600  # stat.S_IRUSR | stat.S_IWUSR


def test_save_works_without_fchmod_attribute(tmp_path) -> None:
    """Issue #3748: save() should work even if os.fchmod attribute is missing entirely.

    This is a more aggressive test that simulates the exact Windows condition
    where the attribute doesn't exist at all.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Temporarily remove fchmod from os module
    original_fchmod = getattr(os, "fchmod", None)
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise an exception
        storage.save([Todo(id=1, text="test")])

        # Verify the file was saved correctly
        assert db.exists()
        content = db.read_text()
        assert '"text": "test"' in content
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod

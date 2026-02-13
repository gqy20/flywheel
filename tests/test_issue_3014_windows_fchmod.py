"""Regression tests for issue #3014: os.fchmod not available on Windows.

Issue: os.fchmod is Unix-only and raises AttributeError on Windows platform.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_does_not_raise_attributeerror_when_fchmod_unavailable(tmp_path) -> None:
    """Issue #3014: save() should not raise AttributeError when os.fchmod is unavailable.

    On Windows, os.fchmod does not exist. This test simulates that environment
    by mocking os.fchmod to None.

    Before fix: Raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: Falls back to os.chmod and completes successfully.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    with mock.patch.object(os, 'fchmod', None):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test todo")])

    # Verify the file was actually saved
    assert db.exists()
    content = db.read_text()
    assert "test todo" in content


def test_save_uses_fchmod_on_unix_when_available(tmp_path) -> None:
    """Issue #3014: On Unix, save() should still use os.fchmod for security.

    This verifies that the fix doesn't break the existing secure behavior
    on Unix platforms where os.fchmod is available.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track if os.fchmod was called
    fchmod_called = []

    original_fchmod = os.fchmod if hasattr(os, 'fchmod') else None

    def tracking_fchmod(fd, mode):
        fchmod_called.append((fd, mode))
        if original_fchmod:
            original_fchmod(fd, mode)

    with mock.patch.object(os, 'fchmod', tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # On Unix, fchmod should have been called
    # On Windows (CI that has fchmod), it should also be called
    assert len(fchmod_called) > 0, "os.fchmod should be called when available"

    # Verify the mode was 0o600
    _, mode = fchmod_called[0]
    assert mode == stat.S_IRUSR | stat.S_IWUSR, f"Expected mode 0o600, got {oct(mode)}"


def test_save_fallback_to_chmod_sets_correct_permissions(tmp_path) -> None:
    """Issue #3014: When falling back to os.chmod, permissions should still be 0o600."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    chmod_calls = []

    original_chmod = os.chmod

    def tracking_chmod(path, mode, *args, **kwargs):
        chmod_calls.append((path, mode))
        original_chmod(path, mode, *args, **kwargs)

    # Simulate fchmod unavailable, track chmod calls
    with (
        mock.patch.object(os, 'fchmod', None),
        mock.patch.object(os, 'chmod', tracking_chmod),
    ):
        storage.save([Todo(id=1, text="test")])

    # chmod should have been called with 0o600
    assert len(chmod_calls) > 0, "os.chmod should be called as fallback"

    for _path, mode in chmod_calls:
        assert mode == stat.S_IRUSR | stat.S_IWUSR, (
            f"Expected mode 0o600, got {oct(mode)}"
        )

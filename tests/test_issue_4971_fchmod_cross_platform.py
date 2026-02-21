"""Regression tests for issue #4971: os.fchmod is not available on Windows.

Issue: os.fchmod is a POSIX-specific function that doesn't exist on Windows.
On Windows, this causes an AttributeError when attempting to set file permissions.

These tests verify cross-platform compatibility.
"""

from __future__ import annotations

import os
import stat
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_succeeds_when_fchmod_not_available(tmp_path) -> None:
    """Issue #4971: save() should succeed on systems where os.fchmod is unavailable.

    Before fix: AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() should gracefully skip permission setting on non-POSIX systems
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate a system without os.fchmod (like Windows)
    with mock.patch.object(os, 'fchmod', None):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test")])

    # Verify save succeeded
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_save_succeeds_without_fchmod_attribute(tmp_path) -> None:
    """Issue #4971: save() should work when os.fchmod attribute is missing entirely.

    Some systems may not have the fchmod attribute at all.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Store original value
    original_fchmod = getattr(os, 'fchmod', None)

    # Remove fchmod entirely to simulate a system without it
    if hasattr(os, 'fchmod'):
        delattr(os, 'fchmod')

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test")])

        # Verify save succeeded
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_fchmod_used_when_available(tmp_path, monkeypatch) -> None:
    """Issue #4971: fchmod should still be used on POSIX systems where available.

    This test verifies that on POSIX systems, we still call fchmod to set
    restrictive permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track if fchmod was called
    fchmod_calls = []

    # Skip this test if fchmod is not available on this system
    if not hasattr(os, 'fchmod'):
        import pytest
        pytest.skip("os.fchmod not available on this system")

    original_fchmod = os.fchmod

    def mock_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    monkeypatch.setattr(os, 'fchmod', mock_fchmod)

    storage.save([Todo(id=1, text="test")])

    # Verify fchmod was called with restrictive permissions
    assert len(fchmod_calls) == 1, "fchmod should have been called once"
    assert fchmod_calls[0][1] == stat.S_IRUSR | stat.S_IWUSR, \
        f"Expected mode 0o600, got {oct(fchmod_calls[0][1])}"


def test_save_creates_file_on_all_platforms(tmp_path) -> None:
    """Issue #4971: save() should successfully create files on all platforms.

    This is a basic smoke test to ensure the fix doesn't break normal operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]

    # Should succeed on any platform
    storage.save(todos)

    # Verify content
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True

    # Verify file exists
    assert db.exists()

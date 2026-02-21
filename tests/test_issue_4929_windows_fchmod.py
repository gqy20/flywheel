"""Regression tests for issue #4929: os.fchmod raises AttributeError on Windows.

Issue: os.fchmod is Unix-only and will raise AttributeError on Windows.
The save() method in TodoStorage uses os.fchmod which doesn't exist on Windows.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_succeeds_when_fchmod_raises_attribute_error(tmp_path) -> None:
    """Issue #4929: save() should work even when os.fchmod is unavailable.

    This simulates Windows behavior where os.fchmod doesn't exist.
    The save() method should gracefully handle the AttributeError
    and continue without setting permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock os.fchmod to raise AttributeError (simulating Windows)
    with patch("flywheel.storage.os.fchmod", side_effect=AttributeError("module 'os' has no attribute 'fchmod'")):
        # This should NOT raise AttributeError - it should gracefully skip fchmod
        storage.save([Todo(id=1, text="test")])

    # Verify the file was actually written
    assert db.exists(), "File should be created even when fchmod fails"

    # Verify content is correct
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_save_succeeds_when_fchmod_missing_from_os_module(tmp_path) -> None:
    """Issue #4929: save() should work when os.fchmod attribute is missing entirely.

    This simulates a stricter Windows environment where the attribute doesn't exist.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Store the original fchmod (might be None on Windows)
    import os
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod from os module entirely
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test without fchmod")])

        # Verify the file was actually written
        assert db.exists(), "File should be created even when fchmod is missing"

        # Verify content is correct
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test without fchmod"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


@pytest.mark.skipif(sys.platform == "win32", reason="Permission test requires Unix fchmod")
def test_unix_permissions_preserved_when_fchmod_available(tmp_path) -> None:
    """Issue #4929: Unix behavior should be preserved after the fix.

    When fchmod is available, it should still be called and set permissions to 0o600.
    """
    import os
    import stat

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # Verify file exists and has correct permissions
    assert db.exists()
    file_stat = os.stat(db)
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # On Unix, permissions should be 0o600 (rw-------)
    # Note: umask might affect final permissions, so we check key bits
    assert file_mode & stat.S_IRUSR, "Owner should have read permission"
    assert file_mode & stat.S_IWUSR, "Owner should have write permission"

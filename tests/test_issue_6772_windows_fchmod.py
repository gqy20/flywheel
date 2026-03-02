"""Regression tests for issue #6772: os.fchmod is Unix-only.

Issue: os.fchmod raises AttributeError on Windows because it's a POSIX-only API.
The save() method should gracefully handle this and continue working.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_gracefully(tmp_path: Path) -> None:
    """Issue #6777: save() must not crash with AttributeError when os.fchmod is unavailable.

    Simulates Windows behavior where os.fchmod doesn't exist by raising AttributeError.
    The save operation should complete successfully without crashing.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by making fchmod raise AttributeError
    with patch.object(os, "fchmod", side_effect=AttributeError("module 'os' has no attribute 'fchmod'")):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test todo")])

    # Verify the data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_works_when_fchmod_attribute_missing(tmp_path: Path) -> None:
    """Issue #6772: save() should work even when os has no fchmod attribute.

    This simulates the actual Windows condition more directly by
    temporarily removing the fchmod attribute from os module.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Store original fchmod if it exists
    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod to simulate Windows
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="windows test"), Todo(id=2, text="another todo")])

        # Verify the data was saved correctly
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "windows test"
        assert loaded[1].text == "another todo"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_temp_file_cleaned_up_on_missing_fchmod(tmp_path: Path) -> None:
    """Issue #6772: Temp files should still be cleaned up properly on Windows.

    Even when fchmod is unavailable, the temp file cleanup mechanism
    should continue to work correctly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track temp files
    temp_files = []
    import tempfile
    original_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files.append(Path(path))
        return fd, path

    with (
        patch.object(os, "fchmod", side_effect=AttributeError("module 'os' has no attribute 'fchmod'")),
        patch.object(tempfile, "mkstemp", tracking_mkstemp),
    ):
        storage.save([Todo(id=1, text="cleanup test")])

    # Temp files should not remain after successful save
    # (they should have been renamed to the target file)
    for temp_file in temp_files:
        assert not temp_file.exists(), f"Temp file should have been renamed: {temp_file}"

    # Final file should exist
    assert db.exists(), "Final database file should exist"

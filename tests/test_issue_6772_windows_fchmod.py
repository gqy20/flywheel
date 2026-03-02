"""Regression tests for issue #6772: os.fchmod is Unix-only.

Issue: os.fchmod raises AttributeError on Windows because it's a POSIX-only API.
The save() function should handle this gracefully rather than crashing.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_on_windows(tmp_path) -> None:
    """Issue #6772: save() must not crash with AttributeError on Windows.

    os.fchmod is not available on Windows. When it raises AttributeError
    (or doesn't exist), the save operation should still complete successfully.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully on Windows
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by making fchmod raise AttributeError
    with patch.object(os, 'fchmod', side_effect=AttributeError("module 'os' has no attribute 'fchmod'")):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test todo")])

    # Verify the save actually completed
    assert db.exists()
    content = db.read_text()
    assert "test todo" in content


def test_save_works_when_fchmod_does_not_exist(tmp_path) -> None:
    """Issue #6772: save() must work when os.fchmod attribute doesn't exist.

    On Windows, os.fchmod simply doesn't exist as an attribute.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save the original fchmod (may not exist on Windows)
    original_fchmod = getattr(os, 'fchmod', None)

    # Remove fchmod to simulate Windows
    if hasattr(os, 'fchmod'):
        delattr(os, 'fchmod')

    try:
        # This should NOT crash
        storage.save([Todo(id=2, text="another test")])

        # Verify the save completed
        assert db.exists()
        content = db.read_text()
        assert "another test" in content
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_completes_and_cleanup_on_windows(tmp_path) -> None:
    """Issue #6772: Verify temp file cleanup still works on Windows.

    Even without fchmod, temp files should be properly cleaned up on errors.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track temp files created
    temp_files_created = []

    original_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    with patch.object(os, 'fchmod', side_effect=AttributeError("module 'os' has no attribute 'fchmod'")), \
         patch.object(tempfile, 'mkstemp', side_effect=tracking_mkstemp):
        storage.save([Todo(id=3, text="cleanup test")])

    # Verify final file exists
    assert db.exists()

    # Temp files should be cleaned up (renamed to final path)
    for temp_file in temp_files_created:
        assert not temp_file.exists(), f"Temp file not cleaned up: {temp_file}"

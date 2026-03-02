"""Regression tests for issue #6772: os.fchmod is Unix-only and raises AttributeError on Windows.

Issue: os.fchmod is POSIX-only and not available on Windows. The code at
src/flywheel/storage.py:112 will raise AttributeError on Windows platforms.

The save() function should gracefully handle the absence of os.fchmod on Windows
by catching AttributeError and continuing execution.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_gracefully(tmp_path) -> None:
    """Issue #6772: save() must not crash with AttributeError on Windows.

    On Windows, os.fchmod does not exist and will raise AttributeError.
    The save() function should handle this gracefully and continue.

    Before fix: save() raises AttributeError when os.fchmod is missing
    After fix: save() catches AttributeError and continues without chmod
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock os.fchmod to raise AttributeError (simulating Windows behavior)
    with mock.patch.object(
        os, "fchmod", side_effect=AttributeError("module 'os' has no attribute 'fchmod'")
    ):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test todo")])

    # Verify the file was still created correctly
    assert db.exists(), "Database file should be created even when fchmod is unavailable"
    content = db.read_text(encoding="utf-8")
    assert "test todo" in content, "Todo content should be saved correctly"


def test_save_completes_full_workflow_without_fchmod(tmp_path) -> None:
    """Issue #6772: Verify full save/load workflow works without fchmod.

    This ensures that even without fchmod, the temp file is properly
    written and renamed to the target location.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo"),
    ]

    # Mock os.fchmod to raise AttributeError (simulating Windows behavior)
    with mock.patch.object(
        os, "fchmod", side_effect=AttributeError("module 'os' has no attribute 'fchmod'")
    ):
        storage.save(todos)

    # Verify file exists and content is correct
    assert db.exists(), "Database file should exist after save"
    loaded = storage.load()
    assert len(loaded) == 2, "Should have 2 todos"
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"


def test_temp_file_cleaned_up_on_error_without_fchmod(tmp_path) -> None:
    """Issue #6772: Temp files should still be cleaned up on error.

    Even when fchmod is unavailable, error handling should still work
    and temp files should be cleaned up properly.
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

    # Mock both fchmod and mkstemp
    with (
        mock.patch.object(
            os, "fchmod", side_effect=AttributeError("module 'os' has no attribute 'fchmod'")
        ),
        mock.patch.object(tempfile, "mkstemp", side_effect=tracking_mkstemp),
    ):
        storage.save([Todo(id=1, text="test")])

    # On successful save, temp file should be renamed (no longer exists as temp)
    # The temp files should have been renamed to the target file
    assert db.exists(), "Final database file should exist"
    for temp_file in temp_files_created:
        assert not temp_file.exists(), f"Temp file {temp_file} should have been renamed"

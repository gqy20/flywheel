"""Regression tests for issue #4132: TOCTOU race condition in _ensure_parent_directory.

Issue: There's a Time-of-Check to Time-of-Use (TOCTOU) race condition between
the path existence check and the mkdir() call in _ensure_parent_directory.
If another process creates the directory between exists() and mkdir(),
the operation fails with FileExistsError.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_toctou_race_condition_in_ensure_parent_directory(tmp_path) -> None:
    """Issue #4132: Should handle concurrent directory creation gracefully.

    This test simulates the TOCTOU race condition by having the mock
    create the directory AFTER exists() returns False but BEFORE mkdir() runs.
    With the fix (exist_ok=True), this should succeed without FileExistsError.
    """
    db_path = tmp_path / "subdir" / "todo.json"
    storage = TodoStorage(str(db_path))
    todos = [Todo(id=1, text="test todo")]

    # Track whether the race condition was triggered
    race_triggered = False
    original_exists = Path.exists
    original_mkdir = Path.mkdir

    def mock_exists(self) -> bool:
        """Return False for the parent directory to trigger mkdir path."""
        if str(self) == str(tmp_path / "subdir"):
            return False  # Parent doesn't exist, so mkdir will be called
        return original_exists(self)

    def mock_mkdir(self, *args, **kwargs) -> None:
        """Simulate race condition: create directory just before mkdir runs."""
        nonlocal race_triggered
        if str(self) == str(tmp_path / "subdir"):
            # Simulate another process creating the directory
            # between exists() check and mkdir() call
            original_mkdir(self, parents=True, exist_ok=True)
            race_triggered = True
        # Now call the actual mkdir - with exist_ok=False (old behavior),
        # this would raise FileExistsError
        # With exist_ok=True (fix), this should succeed
        original_mkdir(self, *args, **kwargs)

    # Patch both exists and mkdir to simulate the race
    with (
        patch.object(Path, "exists", mock_exists),
        patch.object(Path, "mkdir", mock_mkdir),
    ):
        # Before fix: this would raise FileExistsError
        # After fix: this should succeed
        storage.save(todos)

    # Verify the race condition was actually triggered
    assert race_triggered, "Test setup error: race condition was not triggered"

    # Verify the data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_concurrent_parent_directory_creation_succeeds(tmp_path) -> None:
    """Issue #4132: Verify that concurrent directory creation doesn't cause failure.

    This is a more direct test that verifies the fix works by testing
    that using exist_ok=True handles the case where directory already exists.
    """
    db_path = tmp_path / "newdir" / "todo.json"
    storage = TodoStorage(str(db_path))
    todos = [Todo(id=1, text="concurrent test")]

    # Pre-create the parent directory (simulating another process)
    (tmp_path / "newdir").mkdir(parents=True, exist_ok=True)

    # This should succeed even though directory was created concurrently
    # With the fix (exist_ok=True), this works
    storage.save(todos)

    # Verify data was saved
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "concurrent test"


def test_ensure_parent_directory_idempotent(tmp_path) -> None:
    """Issue #4132: Calling _ensure_parent_directory multiple times should be safe.

    With exist_ok=True, calling mkdir on an already-existing directory
    should not raise an error.
    """
    from flywheel.storage import _ensure_parent_directory

    db_path = tmp_path / "repeated" / "todo.json"

    # First call - creates the directory
    _ensure_parent_directory(db_path)

    # Second call - directory already exists, should be idempotent
    _ensure_parent_directory(db_path)

    # Third call for good measure
    _ensure_parent_directory(db_path)

    # Verify the parent directory exists
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()

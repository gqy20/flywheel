"""Regression test for issue #5528: save() fails with FileNotFoundError when parent directory doesn't exist.

This test verifies that save() correctly creates parent directories before
attempting to create the temp file with mkstemp.

The issue was a TOCTOU (Time-of-Check-Time-of-Use) race condition in
_ensure_parent_directory where exist_ok=False could cause failures if
another process created the directory between the exists() check and mkdir().
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_save_creates_missing_parent_directories(tmp_path) -> None:
    """Test that save() succeeds when called on a path with non-existent parent directories.

    This is a regression test for issue #5528.
    The save() method should create all necessary parent directories before
    creating the temp file, not fail with FileNotFoundError.
    """
    # Create a path where neither newdir nor subdir exist
    db_path = tmp_path / "newdir" / "subdir" / "todo.json"

    # Verify the parent directories don't exist
    assert not db_path.parent.exists()
    assert not (tmp_path / "newdir").exists()

    storage = TodoStorage(str(db_path))
    todos = [Todo(id=1, text="test todo")]

    # This should NOT raise FileNotFoundError
    # It should create parent directories and save successfully
    storage.save(todos)

    # Verify the file was saved correctly
    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_ensure_parent_directory_handles_race_condition(tmp_path) -> None:
    """Test that _ensure_parent_directory handles TOCTOU race condition.

    This test simulates the race condition where another process creates
    the directory between our exists() check and mkdir() call.
    The function should succeed with exist_ok=True instead of failing.
    """
    db_path = tmp_path / "race_dir" / "todo.json"
    parent = db_path.parent

    # Verify parent doesn't exist initially
    assert not parent.exists()

    # Simulate TOCTOU race: mock Path.mkdir to create directory before our mkdir
    original_mkdir = Path.mkdir

    def mkdir_with_race(self, *args, **kwargs):
        # Simulate another process creating the directory
        if self == parent and not self.exists():
            # Create the directory as if another process did it
            original_mkdir(self, parents=kwargs.get("parents", False), exist_ok=True)
        # Now proceed with the actual mkdir call
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", mkdir_with_race):
        # This should NOT raise FileExistsError due to race condition
        _ensure_parent_directory(db_path)

    # Verify directory was created
    assert parent.exists()


def test_save_creates_deeply_nested_parent_directories(tmp_path) -> None:
    """Test save() with deeply nested non-existent parent directories."""
    # Create a path with multiple levels of non-existent directories
    db_path = tmp_path / "level1" / "level2" / "level3" / "level4" / "todo.json"

    # Verify none of the parent directories exist
    assert not db_path.parent.exists()

    storage = TodoStorage(str(db_path))
    todos = [Todo(id=1, text="nested todo")]

    # This should succeed by creating all parent directories
    storage.save(todos)

    # Verify
    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "nested todo"


def test_save_to_existing_parent_directory_still_works(tmp_path) -> None:
    """Verify that the fix doesn't break the normal case where parent directory exists."""
    db_path = tmp_path / "todo.json"

    storage = TodoStorage(str(db_path))
    todos = [Todo(id=1, text="normal case")]

    # Parent (tmp_path) already exists, this should still work
    storage.save(todos)

    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "normal case"

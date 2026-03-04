"""Regression tests for issue #7175: TOCTOU race condition in _ensure_parent_directory.

Issue: There's a race window between checking if parent paths are files (line 35-40)
and creating the directory (line 43-50). An attacker could create a file at a parent
path during this window, bypassing the check.

The fix uses exist_ok=True with mkdir and catches FileExistsError to detect when
a file (not directory) exists at a parent path, eliminating the race window.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_detects_file_at_parent_path(tmp_path) -> None:
    """Issue #7175: _ensure_parent_directory should fail if parent is a file.

    This is the core issue: if a file exists where we need a directory,
    the operation should fail with a clear error.
    """
    # Create a file at parent path
    conflicting_file = tmp_path / "subdir"
    conflicting_file.write_text("I am a file")

    # Path that needs "subdir" to be a directory
    db_path = tmp_path / "subdir" / "db.json"

    # Should raise an error because parent is a file
    with pytest.raises((ValueError, OSError, NotADirectoryError, FileExistsError)) as exc_info:
        _ensure_parent_directory(db_path)

    # Error should be clear about the problem
    error_msg = str(exc_info.value).lower()
    assert "file" in error_msg or "directory" in error_msg or "path" in error_msg


def test_ensure_parent_directory_handles_toctou_race(tmp_path) -> None:
    """Issue #7175: _ensure_parent_directory should handle TOCTOU race safely.

    The fix uses exist_ok=True with mkdir and catches FileExistsError to detect
    when a file (not directory) was created at the parent path during the race window.

    This test simulates the race condition by calling _ensure_parent_directory
    when a file already exists at the parent path (simulating what happens
    if an attacker creates a file in the race window).
    """
    # Setup path that needs parent creation
    db_path = tmp_path / "raceparent" / "db.json"

    # Pre-create a file at the parent path
    # This simulates what an attacker could do in the TOCTOU race window
    race_file = tmp_path / "raceparent"
    race_file.write_text("attacker created this file")

    # Now call _ensure_parent_directory - it should detect the file
    # and raise a clear error instead of silently succeeding
    with pytest.raises((ValueError, OSError, NotADirectoryError, FileExistsError)) as exc_info:
        _ensure_parent_directory(db_path)

    # Error message should be clear about what went wrong
    error_msg = str(exc_info.value).lower()
    assert any(
        keyword in error_msg
        for keyword in ["file", "directory", "path", "exists", "not a directory"]
    ), f"Error message should indicate the problem: {exc_info.value}"


def test_storage_save_fails_when_parent_is_file(tmp_path) -> None:
    """Issue #7175: TodoStorage.save() should fail safely when parent path is a file.

    This is the user-facing behavior: attempting to save to a path where
    a parent component is a file (not a directory) should fail with a clear error.
    """
    # Create a file where we need a directory
    parent_as_file = tmp_path / "blocked"
    parent_as_file.write_text("I am a file, not a directory")

    # Try to save to a path that requires "blocked" to be a directory
    db_path = tmp_path / "blocked" / "db.json"
    storage = TodoStorage(str(db_path))

    # Should fail with a clear error
    with pytest.raises((ValueError, OSError, NotADirectoryError, FileExistsError)) as exc_info:
        storage.save([Todo(id=1, text="test")])

    # Error should mention the path problem
    error_msg = str(exc_info.value).lower()
    assert "file" in error_msg or "directory" in error_msg or "path" in error_msg


def test_normal_directory_creation_still_works(tmp_path) -> None:
    """Issue #7175: Normal directory creation should still work after the fix.

    This is a regression test to ensure the fix doesn't break normal operation.
    """
    # Create a deeply nested path that doesn't exist
    db_path = tmp_path / "a" / "b" / "c" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should succeed
    storage.save([Todo(id=1, text="test")])

    # Verify file was created
    assert db_path.exists()

    # Verify content
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_save_to_existing_directory_works(tmp_path) -> None:
    """Issue #7175: Saving to existing directory should still work."""
    # Pre-create the parent directory
    parent_dir = tmp_path / "existing"
    parent_dir.mkdir()

    db_path = parent_dir / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should succeed
    storage.save([Todo(id=1, text="test")])
    assert db_path.exists()


def test_nested_file_parent_detection(tmp_path) -> None:
    """Issue #7175: Detect file-as-parent at any level of the path hierarchy.

    Tests that we detect when a file exists at any parent level, not just
    the immediate parent.
    """
    # Create a file at an intermediate level
    intermediate_file = tmp_path / "level1" / "level2.json"
    intermediate_file.parent.mkdir(parents=True)
    intermediate_file.write_text("I am a file at level2")

    # Try to save to a path that requires level2.json to be a directory
    db_path = tmp_path / "level1" / "level2.json" / "level3" / "db.json"
    storage = TodoStorage(str(db_path))

    # Should fail because level2.json is a file, not a directory
    with pytest.raises((ValueError, OSError, NotADirectoryError, FileExistsError)):
        storage.save([Todo(id=1, text="test")])


def test_toctou_race_condition_exploitation(tmp_path) -> None:
    """Issue #7175: Demonstrate and test the TOCTOU race condition fix.

    The fix uses exist_ok=True with mkdir and catches FileExistsError to detect
    when a file (not directory) was created at the parent path during the race window.

    This test injects a file at the parent path during the mkdir call to simulate
    the race condition and verify the fix properly detects it.
    """
    db_path = tmp_path / "race_parent" / "db.json"
    parent_path = tmp_path / "race_parent"

    original_mkdir = Path.mkdir

    def patched_mkdir(self, *args, **kwargs):
        """Patch Path.mkdir to inject a file before the actual mkdir call."""
        if self == parent_path:
            # Inject a file at the parent path before the actual mkdir
            # This simulates an attacker creating a file in the race window
            parent_path.write_text("attacker created this file")
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", patched_mkdir):
        storage = TodoStorage(str(db_path))
        # This should fail safely with a clear error, not succeed silently
        with pytest.raises((ValueError, OSError, NotADirectoryError, FileExistsError)) as exc_info:
            storage.save([Todo(id=1, text="test")])

        # Error message should be clear about the problem
        error_msg = str(exc_info.value).lower()
        assert any(
            keyword in error_msg
            for keyword in ["file", "directory", "path", "exists", "not a directory"]
        ), f"Error message should indicate the problem: {exc_info.value}"


def test_toctou_race_creates_directory_robustly(tmp_path) -> None:
    """Issue #7175: Verify directory creation is robust against TOCTOU races.

    The fix should use exist_ok=True with mkdir() to handle the case where
    the directory was created by another process between the check and mkdir.
    This test verifies that scenario works correctly.
    """
    db_path = tmp_path / "concurrent_parent" / "db.json"
    parent_path = tmp_path / "concurrent_parent"

    mkdir_called = threading.Event()
    original_mkdir = Path.mkdir

    def patched_mkdir(self, *args, **kwargs):
        """Inject directory creation by another process during mkdir call."""
        if self == parent_path:
            # Simulate another process creating the directory
            original_mkdir(self, parents=True, exist_ok=True)
            mkdir_called.set()
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", patched_mkdir):
        storage = TodoStorage(str(db_path))
        # Should succeed even though directory was created concurrently
        storage.save([Todo(id=1, text="test")])

    # Verify the file was created correctly
    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"

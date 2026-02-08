"""Regression tests for issue #2179: Race condition in _ensure_parent_directory.

Issue: _ensure_parent_directory has a TOCTOU race condition between the exists()
check (line 43) and mkdir() call (line 45) when exist_ok=False.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from flywheel.storage import _ensure_parent_directory


def test_concurrent_directory_creation_succeeds(tmp_path) -> None:
    """Issue #2179: Concurrent calls to create the same directory should both succeed.

    Before fix: Raises FileExistsError when two threads race to create same directory
    After fix: Both calls succeed with exist_ok=True
    """
    # Create a path that doesn't exist
    target_path = tmp_path / "race" / "dir" / "todo.json"

    # Track results from both threads
    results = []
    errors = []

    def create_parent_dir() -> None:
        """Function to be called by multiple threads concurrently."""
        try:
            _ensure_parent_directory(target_path)
            results.append("success")
        except Exception as e:
            errors.append(e)

    # Create two threads that will race to create the same directory
    thread1 = threading.Thread(target=create_parent_dir)
    thread2 = threading.Thread(target=create_parent_dir)

    # Start both threads simultaneously
    thread1.start()
    thread2.start()

    # Wait for both to complete
    thread1.join()
    thread2.join()

    # Both should succeed - no errors should occur
    assert len(errors) == 0, f"Both threads should succeed, but got errors: {errors}"
    assert len(results) == 2, "Both threads should complete successfully"

    # Verify the directory was created
    assert target_path.parent.exists(), "Parent directory should exist"
    assert target_path.parent.is_dir(), "Parent should be a directory"


def test_consecutive_calls_to_same_path_succeed(tmp_path) -> None:
    """Issue #2179: Multiple consecutive calls with exist_ok=True should succeed."""
    target_path = tmp_path / "consecutive" / "dir" / "todo.json"

    # First call - creates the directory
    _ensure_parent_directory(target_path)
    assert target_path.parent.exists()

    # Second call - should not raise FileExistsError with exist_ok=True
    # This simulates the race condition where the second caller finds it already exists
    _ensure_parent_directory(target_path)


def test_file_as_directory_validation_still_works(tmp_path) -> None:
    """Issue #2179: Fix should not break existing security validation from issue #1894."""
    # Create a file where a directory should be
    blocking_file = tmp_path / "blocking_file.txt"
    blocking_file.write_text("I am a file")

    # Try to create a directory path that would require the file to be a directory
    target_path = blocking_file / "subdir" / "todo.json"

    # Should still raise ValueError because the file-as-directory validation
    # happens BEFORE the mkdir call
    with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
        _ensure_parent_directory(target_path)


def test_immediate_parent_is_file_raises_error(tmp_path) -> None:
    """Issue #2179: Should still fail when immediate parent is a file."""
    # Create a file at the immediate parent location
    parent_file = tmp_path / "parent.json"
    parent_file.write_text("{}")

    # Try to use a path that requires the file to be a directory
    target_path = parent_file / "todo.json"

    # Should raise ValueError from pre-validation, not FileExistsError from mkdir
    with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
        _ensure_parent_directory(target_path)


def test_normal_nested_directory_creation_still_works(tmp_path) -> None:
    """Issue #2179: Normal nested directory creation should work as before."""
    # Create a deeply nested path
    target_path = tmp_path / "a" / "b" / "c" / "d" / "todo.json"

    # Should succeed without errors
    _ensure_parent_directory(target_path)

    # Verify all parent directories were created
    assert target_path.parent.exists()
    assert target_path.parent.is_dir()

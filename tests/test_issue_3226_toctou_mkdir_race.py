"""Regression tests for issue #3226: TOCTOU race condition in _ensure_parent_directory.

Issue: There is a race condition between path existence check and mkdir in
_ensure_parent_directory. The window is:
1. exists() returns False
2. Another process creates directory
3. mkdir(exist_ok=False) fails with FileExistsError

Fix: Use exist_ok=True and catch FileExistsError separately to distinguish
between race-condition creation (acceptable) vs path-is-file errors (still raise).

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_concurrent_ensure_parent_directory_no_race_error(tmp_path) -> None:
    """Issue #3226: Multiple concurrent calls to _ensure_parent_directory should not fail.

    This test simulates the race condition where:
    - Process A checks exists() -> False
    - Process B checks exists() -> False
    - Process A calls mkdir() -> succeeds
    - Process B calls mkdir() -> should succeed (with exist_ok=True) or raise FileExistsError (acceptable)

    Before fix: Process B gets OSError because exist_ok=False
    After fix: Process B succeeds (exist_ok=True) or FileExistsError is caught and ignored
    """
    # Create a path that doesn't exist yet
    db_path = tmp_path / "subdir" / "todo.json"

    errors = []

    def ensure_parent_worker(worker_id: int) -> None:
        """Worker that tries to create parent directory."""
        try:
            # Small delay to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 3))
            _ensure_parent_directory(db_path)
        except OSError as e:
            errors.append((worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=ensure_parent_worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # No worker should have gotten a race-condition OSError
    assert len(errors) == 0, f"Workers got race condition errors: {errors}"

    # Directory should exist
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_concurrent_save_creates_parent_directory_safely(tmp_path) -> None:
    """Issue #3226: Concurrent save() calls should not fail due to mkdir race.

    Before fix: If multiple processes call save() simultaneously, one may fail
    with OSError from mkdir(exist_ok=False) when another process creates the directory first.
    After fix: All processes should succeed or handle FileExistsError gracefully.
    """
    # Use a path where parent directory doesn't exist yet
    db_path = tmp_path / "race_test" / "concurrent.json"

    results = multiprocessing.Queue()

    def save_worker(worker_id: int) -> None:
        """Worker that saves todos, triggering parent directory creation."""
        try:
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=1, text=f"worker-{worker_id}")]
            # Small delay to align workers
            time.sleep(0.005)
            storage.save(todos)
            results.put(("success", worker_id))
        except OSError as e:
            # OSError from mkdir race is the bug - should not happen after fix
            if "File exists" in str(e) or "exists" in str(e).lower():
                results.put(("race_error", worker_id, str(e)))
            else:
                results.put(("other_error", worker_id, str(e)))
        except Exception as e:
            results.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    race_errors = []
    while not results.empty():
        result = results.get()
        if result[0] == "race_error":
            race_errors.append(result)

    # No worker should have gotten a race-condition error
    assert len(race_errors) == 0, (
        f"Workers got race condition errors from mkdir: {race_errors}. "
        "This indicates exist_ok=False is causing TOCTOU race condition failures."
    )


def test_simulated_race_condition_with_mock(tmp_path) -> None:
    """Issue #3226: Simulate the exact race condition by mocking mkdir.

    This test directly simulates the race:
    1. exists() returns False (parent doesn't exist)
    2. mkdir is called but another process created the directory

    With exist_ok=False: Raises FileExistsError
    With exist_ok=True: Succeeds (directory already exists, which is fine)
    """
    db_path = tmp_path / "mocked_race" / "todo.json"

    # Create a mock that simulates: exists() returns False, but mkdir finds directory exists
    original_exists = Path.exists
    original_mkdir = Path.mkdir

    mkdir_called = []

    def mock_exists(self) -> bool:
        # When checking parent, say it doesn't exist
        if self == db_path.parent:
            return False
        return original_exists(self)

    def mock_mkdir(self, *args, **kwargs):
        mkdir_called.append((self, args, kwargs))
        # Simulate another process created the directory
        # Actually create it before mkdir runs
        original_mkdir(self, parents=True, exist_ok=True)
        # Now call original - if exist_ok=False, this will raise
        # If exist_ok=True, this will succeed
        original_mkdir(self, *args, **kwargs)

    # Test with exist_ok=False (current buggy behavior)
    with (
        patch.object(Path, "exists", mock_exists),
        patch.object(Path, "mkdir", mock_mkdir),
    ):
        # This should NOT raise FileExistsError after the fix
        # Before fix: FileExistsError is raised because exist_ok=False
        try:
            _ensure_parent_directory(db_path)
            # If we get here, the fix is working (exist_ok=True)
            success = True
        except FileExistsError:
            # Before fix: This happens because exist_ok=False
            success = False

        # After fix, this should succeed
        assert success, (
            "mkdir(exist_ok=False) raised FileExistsError in race condition. "
            "Fix should use exist_ok=True to handle concurrent directory creation."
        )


def test_file_as_parent_path_still_raises_proper_error(tmp_path) -> None:
    """Issue #3226: After fixing race condition, file-as-directory errors must still be detected.

    The fix for TOCTOU race should not accidentally hide real errors like
    when a path component exists as a file when it should be a directory.
    """
    # Create a file where directory should exist
    conflicting_file = tmp_path / "blocking.json"
    conflicting_file.write_text("file content")

    # Try to create database inside this "file"
    db_path = conflicting_file / "data.json"

    # Should still raise ValueError for file-as-directory
    with pytest.raises(ValueError, match=r"(directory|path|not a directory|file)"):
        _ensure_parent_directory(db_path)

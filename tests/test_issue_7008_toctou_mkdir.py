"""Regression tests for issue #7008: TOCTOU race condition in _ensure_parent_directory.

Issue: Time-of-check to time-of-use race condition between exists() check and mkdir().
The gap between checking if parent exists and creating it allows another process
to create the directory first, causing FileExistsError with exist_ok=False.

Security Impact: An attacker could create a file/symlink at the parent path between
the check and mkdir, causing unexpected failures or security issues.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_concurrent_directory_creation_no_race_condition(tmp_path) -> None:
    """Issue #7008: Concurrent calls to create the same parent directory should not fail.

    Before fix: FileExistsError is raised when multiple processes try to create
    the same directory concurrently due to exist_ok=False.

    After fix: Using exist_ok=True should handle concurrent directory creation
    gracefully without errors.
    """
    db = tmp_path / "subdir1" / "subdir2" / "todo.json"

    def create_directory_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that tries to ensure parent directory exists."""
        try:
            # Each worker tries to create the same parent directory
            _ensure_parent_directory(db)
            result_queue.put(("success", worker_id))
        except FileExistsError as e:
            # This is the bug - race condition causes FileExistsError
            result_queue.put(("race_error", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers that all try to create the same directory
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=create_directory_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    race_errors = [r for r in results if r[0] == "race_error"]
    other_errors = [r for r in results if r[0] == "error"]

    # After fix: No race condition errors should occur
    assert len(race_errors) == 0, f"TOCTOU race condition detected: {race_errors}"
    assert len(other_errors) == 0, f"Other errors occurred: {other_errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"


def test_mkdir_with_exist_ok_true_handles_concurrent_creation(tmp_path) -> None:
    """Issue #7008: mkdir with exist_ok=True should handle concurrent directory creation.

    This test verifies that exist_ok=True is used in the fix.
    """
    db = tmp_path / "concurrent" / "todo.json"

    # Track mkdir calls
    mkdir_calls = []
    original_mkdir = Path.mkdir

    def tracking_mkdir(self, *args, **kwargs):
        mkdir_calls.append({
            "path": str(self),
            "exist_ok": kwargs.get("exist_ok", args[1] if len(args) > 1 else False),
        })
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", tracking_mkdir):
        _ensure_parent_directory(db)

    # After fix: exist_ok should be True
    assert len(mkdir_calls) > 0, "mkdir should have been called"
    for call in mkdir_calls:
        assert call["exist_ok"] is True, (
            f"mkdir should use exist_ok=True to prevent TOCTOU race condition, "
            f"but got exist_ok={call['exist_ok']}"
        )


def test_race_between_exists_check_and_mkdir(tmp_path) -> None:
    """Issue #7008: Test race condition by creating directory between exists() and mkdir().

    Before fix: An attacker/process creating the directory between the exists() check
    and mkdir() call would cause FileExistsError.

    After fix: Using exist_ok=True handles this scenario gracefully.
    """
    db = tmp_path / "race_test" / "todo.json"
    parent = db.parent

    # Simulate race condition by creating the directory during the exists() check
    original_exists = Path.exists
    call_count = [0]

    def race_condition_exists(self):
        result = original_exists(self)
        # On the second call (checking parent.exists()), create the directory
        if self == parent and call_count[0] == 0:
            call_count[0] += 1
            # Simulate another process creating the directory
            parent.mkdir(parents=True, exist_ok=True)
        return result

    with patch.object(Path, "exists", race_condition_exists):
        # Before fix: This would raise FileExistsError
        # After fix: This should succeed
        _ensure_parent_directory(db)

    # Verify directory was created
    assert parent.exists(), "Parent directory should exist"


def test_concurrent_save_creates_parent_directory_safely(tmp_path) -> None:
    """Issue #7008: Multiple processes saving to same new directory should not race.

    Tests the full save() flow with concurrent directory creation.
    """
    db = tmp_path / "shared" / "deeply" / "nested" / "todo.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves todos, requiring parent directory creation."""
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=1, text=f"worker-{worker_id}")]
            storage.save(todos)
            result_queue.put(("success", worker_id))
        except FileExistsError as e:
            # Race condition bug
            result_queue.put(("race_error", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    race_errors = [r for r in results if r[0] == "race_error"]
    other_errors = [r for r in results if r[0] == "error"]

    # After fix: No race condition errors
    assert len(race_errors) == 0, f"TOCTOU race condition in save(): {race_errors}"
    assert len(other_errors) == 0, f"Other errors in save(): {other_errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"


def test_file_as_directory_validation_still_works_with_exist_ok_true(tmp_path) -> None:
    """Issue #7008: Verify file-as-directory validation still works after fix.

    The fix should not bypass the security check that prevents using a file
    as a directory path component.
    """
    # Create a file where a directory should be
    blocking_file = tmp_path / "blocking.json"
    blocking_file.write_text("I am a file")

    # Try to create a path that requires this file to be a directory
    db_path = blocking_file / "subdir" / "todo.json"

    # Should still raise ValueError for file-as-directory confusion
    with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
        _ensure_parent_directory(db_path)

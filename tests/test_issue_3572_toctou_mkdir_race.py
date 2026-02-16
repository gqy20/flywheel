"""Regression tests for issue #3572: TOCTOU race in _ensure_parent_directory.

Issue: The pattern `if not parent.exists(): parent.mkdir()` has a TOCTOU race
where another process could create the directory between the exists() check
and the mkdir() call, causing a FileExistsError.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_is_idempotent(tmp_path: Path) -> None:
    """Issue #3572: _ensure_parent_directory should be safe to call multiple times.

    Before fix: Second call might fail if directory was created by another process
    After fix: Should succeed regardless of whether directory now exists
    """
    # Create a path to a non-existent directory
    db_path = tmp_path / "new_dir" / "todo.json"

    # First call creates the directory
    _ensure_parent_directory(db_path)

    # Second call should NOT raise FileExistsError even though directory exists
    # This tests that the fix uses exist_ok=True
    _ensure_parent_directory(db_path)  # Should not raise

    # Verify directory was created
    assert db_path.parent.is_dir()


def test_concurrent_ensure_parent_directory_no_race(tmp_path: Path) -> None:
    """Issue #3572: Concurrent calls to _ensure_parent_directory should not race.

    Before fix: FileExistsError could be raised if multiple processes race
    After fix: All calls should succeed using exist_ok=True
    """
    db_path = tmp_path / "shared_dir" / "todo.json"
    success_count = multiprocessing.Value("i", 0)
    error_count = multiprocessing.Value("i", 0)

    def worker(worker_id: int) -> None:
        """Worker that calls _ensure_parent_directory concurrently."""
        try:
            # Small random delay to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 3))
            _ensure_parent_directory(db_path)
            with success_count.get_lock():
                success_count.value += 1
        except FileExistsError:
            # This is the bug we're testing for
            with error_count.get_lock():
                error_count.value += 1
        except Exception:
            with error_count.get_lock():
                error_count.value += 1

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # All workers should have succeeded without FileExistsError
    assert error_count.value == 0, (
        f"Got {error_count.value} errors from {num_workers} concurrent calls. "
        "TOCTOU race detected."
    )
    assert success_count.value == num_workers


def test_concurrent_save_creates_parent_directory_no_race(tmp_path: Path) -> None:
    """Issue #3572: Concurrent save() calls should not race on parent directory creation.

    This is the main use case - multiple processes saving to the same new directory.
    Before fix: FileExistsError could be raised
    After fix: All saves should succeed
    """
    db_path = tmp_path / "concurrent_new_dir" / "shared.json"
    results = multiprocessing.Queue()

    def save_worker(worker_id: int) -> None:
        """Worker that saves todos to a new directory."""
        try:
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
            results.put(("success", worker_id))
        except FileExistsError as e:
            results.put(("FileExistsError", worker_id, str(e)))
        except Exception as e:
            results.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently - all trying to save to a new directory
    num_workers = 5
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    worker_results = []
    while not results.empty():
        worker_results.append(results.get())

    # Check for FileExistsError specifically (the bug we're fixing)
    file_exists_errors = [r for r in worker_results if r[0] == "FileExistsError"]
    assert len(file_exists_errors) == 0, (
        f"Got FileExistsError from workers: {file_exists_errors}. "
        "TOCTOU race in _ensure_parent_directory detected."
    )

    # All workers should have succeeded
    successes = [r for r in worker_results if r[0] == "success"]
    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}. "
        f"Results: {worker_results}"
    )


def test_mkdir_with_exist_ok_true_called_directly(tmp_path: Path) -> None:
    """Issue #3572: Verify the fix uses exist_ok=True pattern.

    This test mocks mkdir to verify it's called with exist_ok=True.
    """
    db_path = tmp_path / "test_dir" / "todo.json"

    # Track mkdir call parameters
    mkdir_calls = []
    original_mkdir = Path.mkdir

    def tracking_mkdir(self, *args, **kwargs):
        mkdir_calls.append({"args": args, "kwargs": kwargs})
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", tracking_mkdir):
        _ensure_parent_directory(db_path)

    # Verify mkdir was called with exist_ok=True
    assert len(mkdir_calls) == 1, f"Expected 1 mkdir call, got {len(mkdir_calls)}"
    call = mkdir_calls[0]

    # Check that exist_ok=True is in kwargs
    assert call["kwargs"].get("exist_ok") is True, (
        f"mkdir should be called with exist_ok=True, got: {call}"
    )
    # Check that parents=True is also set
    assert call["kwargs"].get("parents") is True, (
        f"mkdir should be called with parents=True, got: {call}"
    )

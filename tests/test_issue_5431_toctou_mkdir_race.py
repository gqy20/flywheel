"""Regression tests for issue #5431: TOCTOU race in _ensure_parent_directory.

Issue: Between checking parent.exists() and calling parent.mkdir(exist_ok=False),
another process could create the directory, causing FileExistsError.

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


def test_concurrent_mkdir_no_file_exists_error(tmp_path) -> None:
    """Issue #5431: Concurrent mkdir calls should not raise FileExistsError.

    When two processes try to create the same parent directory concurrently,
    both should succeed (or one should gracefully handle the directory already
    existing) without raising FileExistsError.
    """
    # Use a path where parent doesn't exist yet
    db_path = tmp_path / "level1" / "level2" / "todo.json"

    def ensure_parent_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that calls _ensure_parent_directory concurrently."""
        try:
            storage = TodoStorage(str(db_path))
            # Small stagger to increase race likelihood
            time.sleep(0.001 * worker_id)
            _ensure_parent_directory(storage.path)
            result_queue.put(("success", worker_id))
        except FileExistsError as e:
            result_queue.put(("FileExistsError", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=ensure_parent_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # No worker should have encountered FileExistsError
    file_exists_errors = [r for r in results if r[0] == "FileExistsError"]
    assert len(file_exists_errors) == 0, (
        f"Workers encountered FileExistsError (TOCTOU race): {file_exists_errors}"
    )

    # All workers should succeed (at least the directory was created)
    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers, f"Expected all workers to succeed, got: {results}"


def test_concurrent_save_with_new_parent_directory(tmp_path) -> None:
    """Issue #5431: Concurrent save() calls creating new parent directory must not fail.

    This is the real-world scenario: two processes saving to a path where the
    parent directory doesn't exist yet.
    """
    # Use a path where parent doesn't exist yet
    db_path = tmp_path / "newdir" / "subdir" / "todo.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves todos to the same path concurrently."""
        try:
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=1, text=f"worker-{worker_id}-data")]
            # Small stagger to increase race likelihood
            time.sleep(0.001 * worker_id)
            storage.save(todos)
            result_queue.put(("success", worker_id))
        except FileExistsError as e:
            result_queue.put(("FileExistsError", worker_id, str(e)))
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

    # No worker should have encountered FileExistsError
    file_exists_errors = [r for r in results if r[0] == "FileExistsError"]
    assert len(file_exists_errors) == 0, (
        f"Workers encountered FileExistsError (TOCTOU race): {file_exists_errors}"
    )

    # All workers should succeed
    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers, f"Expected all workers to succeed, got: {results}"


def test_file_as_directory_error_still_raised(tmp_path) -> None:
    """Issue #5431: Fix should still catch file-as-directory scenarios.

    The fix must not break the security check: if a file exists where we need
    a directory, we should still raise a clear error.
    """
    # Create a file where a directory is needed
    blocking_file = tmp_path / "blocking.txt"
    blocking_file.write_text("I am a file")

    # Try to create storage that needs blocking_file to be a directory
    db_path = blocking_file / "data.json"
    storage = TodoStorage(str(db_path))

    # Should raise ValueError for file-as-directory, not FileExistsError
    with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
        storage.save([])


def test_mkdir_race_simulation_with_mock(tmp_path) -> None:
    """Issue #5431: Simulate TOCTOU race using mock to force the condition.

    This test mocks parent.exists() to return False, then has mkdir see
    the directory already exists (simulating race condition).
    """
    db_path = tmp_path / "racedir" / "todo.json"

    # Pre-create the directory (simulating another process creating it between exists() and mkdir())
    racedir = tmp_path / "racedir"
    racedir.mkdir(parents=True, exist_ok=True)

    # Now mock exists() to return False (simulating check before other process created dir)
    original_exists = Path.exists

    def mock_exists_return_false(self):
        if self == db_path.parent:
            return False  # Pretend parent doesn't exist
        return original_exists(self)

    with patch.object(Path, "exists", mock_exists_return_false):
        # This should NOT raise FileExistsError even though mkdir(exist_ok=True)
        # would see the directory exists
        try:
            _ensure_parent_directory(db_path)
        except FileExistsError:
            pytest.fail("_ensure_parent_directory raised FileExistsError due to TOCTOU race")

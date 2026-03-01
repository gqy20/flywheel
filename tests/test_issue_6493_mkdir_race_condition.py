"""Regression tests for issue #6493: Race condition in _ensure_parent_directory.

Issue: TOCTOU race condition between exists() check and mkdir() call with exist_ok=False.
The check-then-act pattern creates a window where another process can create the
directory between the check and the mkdir call, causing FileExistsError.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import multiprocessing
import time

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_concurrent_ensure_parent_directory_no_race(tmp_path) -> None:
    """Regression test for issue #6493: Race condition with concurrent mkdir.

    Tests that multiple processes calling _ensure_parent_directory on the same
    path concurrently do not fail with FileExistsError.
    """
    db_path = tmp_path / "race_test" / "subdir" / "test.json"

    errors = multiprocessing.Manager().list()
    barrier = multiprocessing.Barrier(10)  # Synchronize all processes

    def worker(worker_id: int) -> None:
        """Worker that tries to ensure parent directory exists."""
        try:
            # Wait for all workers to be ready (maximize race window)
            barrier.wait(timeout=5)

            # Small additional delay to ensure all hit the exists() check together
            time.sleep(0.001)

            # This should not raise FileExistsError even with concurrent calls
            _ensure_parent_directory(db_path)
        except Exception as e:
            errors.append(f"Worker {worker_id}: {type(e).__name__}: {e}")

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # All workers should succeed without FileExistsError
    assert len(errors) == 0, f"Workers encountered errors: {list(errors)}"

    # Directory should exist
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_concurrent_save_creates_directory_without_error(tmp_path) -> None:
    """Test that concurrent TodoStorage.save() calls create directory atomically.

    This is a higher-level test using the actual TodoStorage API to ensure
    the fix works end-to-end.
    """
    # Use a path where parent directory doesn't exist
    db_path = tmp_path / "concurrent_dir" / "todos.json"

    errors = multiprocessing.Manager().list()
    barrier = multiprocessing.Barrier(5)

    def save_worker(worker_id: int) -> None:
        """Worker that saves todos."""
        try:
            barrier.wait(timeout=5)
            time.sleep(0.001)  # Maximize race window

            storage = TodoStorage(str(db_path))
            todos = [Todo(id=1, text=f"worker-{worker_id}")]
            storage.save(todos)
        except FileExistsError as e:
            # This is the specific error we're fixing - should not happen
            errors.append(f"Worker {worker_id}: FileExistsError: {e}")
        except Exception:
            # Other errors are acceptable (e.g., last-writer-wins behavior)
            pass

    # Run workers concurrently
    num_workers = 5
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i,))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    # No FileExistsError should have occurred
    assert len(errors) == 0, f"FileExistsError occurred: {list(errors)}"


def test_ensure_parent_directory_file_as_parent_still_fails(tmp_path) -> None:
    """Verify that file-as-directory validation still works after the fix.

    The fix changes exist_ok=False to exist_ok=True, but we must ensure
    that the file-as-directory validation (lines 35-40) still works correctly.
    """
    # Create a file where a directory would be needed
    blocking_file = tmp_path / "blocking.json"
    blocking_file.write_text("I am a file")

    # Try to create a path that requires the file to be a directory
    db_path = blocking_file / "subdir" / "test.json"

    # Should still raise ValueError for file-as-directory confusion
    with pytest.raises(ValueError, match=r"(file|directory|Path error)"):
        _ensure_parent_directory(db_path)

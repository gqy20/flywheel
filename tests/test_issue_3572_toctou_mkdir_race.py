"""Regression tests for issue #3572: TOCTOU race in _ensure_parent_directory.

Issue: The pattern `if not parent.exists(): parent.mkdir()` has a race condition
where another process could create the directory between the exists() check and mkdir().

These tests verify that concurrent calls to save() on the same non-existent directory
do not raise FileExistsError.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_concurrent_ensure_parent_directory_no_race(tmp_path) -> None:
    """Issue #3572: Concurrent calls to _ensure_parent_directory should not raise.

    Tests that multiple threads/processes calling _ensure_parent_directory on the
    same non-existent path do not encounter FileExistsError race conditions.
    """
    shared_path = tmp_path / "shared" / "deep" / "path" / "file.json"

    results = multiprocessing.Manager().list()
    errors = multiprocessing.Manager().list()

    def ensure_parent_worker(worker_id: int) -> None:
        """Worker that calls _ensure_parent_directory on shared path."""
        try:
            # Small staggered delay to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 3))
            _ensure_parent_directory(shared_path)
            results.append(worker_id)
        except Exception as e:
            errors.append((worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(target=ensure_parent_worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # All workers should have succeeded without errors
    assert len(list(errors)) == 0, (
        f"Workers encountered race condition errors: {list(errors)}"
    )
    assert len(list(results)) == num_workers

    # Verify directory was created
    assert shared_path.parent.exists()
    assert shared_path.parent.is_dir()


def test_concurrent_save_to_nonexistent_directory_no_race(tmp_path) -> None:
    """Issue #3572: Concurrent save() calls to same new directory should not fail.

    This tests the real-world scenario: multiple processes trying to save todos
    to the same database file whose parent directory doesn't exist yet.
    """
    db_path = tmp_path / "newdb" / "nested" / "todos.json"

    results = multiprocessing.Manager().list()
    errors = multiprocessing.Manager().list()

    def save_worker(worker_id: int) -> None:
        """Worker that saves todos to shared database path."""
        try:
            storage = TodoStorage(str(db_path))
            # Staggered start to increase race likelihood
            time.sleep(0.001 * (worker_id % 5))

            todos = [Todo(id=1, text=f"worker-{worker_id} todo")]
            storage.save(todos)

            results.append(worker_id)
        except Exception as e:
            errors.append((worker_id, str(e), type(e).__name__))

    # Run multiple workers concurrently
    num_workers = 8
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # All workers should have succeeded without FileExistsError
    error_list = list(errors)
    file_exists_errors = [e for e in error_list if "FileExistsError" in str(e)]

    assert len(file_exists_errors) == 0, (
        f"Workers encountered FileExistsError race condition: {file_exists_errors}"
    )

    # Most workers should have succeeded (some may fail on atomic rename last-writer-wins,
    # but that's expected behavior, not the mkdir race we're fixing)
    success_count = len(list(results))
    assert success_count >= num_workers // 2, (
        f"Too many failures: only {success_count}/{num_workers} succeeded. Errors: {error_list}"
    )

    # Verify database file exists and contains valid data
    assert db_path.exists()
    storage = TodoStorage(str(db_path))
    loaded = storage.load()
    assert len(loaded) >= 1


def test_ensure_parent_directory_handles_file_exists_error_gracefully(
    tmp_path,
) -> None:
    """Issue #3572: _ensure_parent_directory should handle FileExistsError gracefully.

    This verifies that even if the directory is created between the check and mkdir,
    the function completes successfully without raising FileExistsError.
    """
    from unittest.mock import patch

    target_path = tmp_path / "raced" / "file.json"
    parent_dir = target_path.parent

    # Track mkdir calls
    mkdir_calls = []

    original_mkdir = Path.mkdir

    def tracking_mkdir(self, *args, **kwargs):
        """Track mkdir calls and simulate race condition on first call."""
        mkdir_calls.append((self, args, kwargs))

        # On the first call to parent.mkdir, create the directory first
        # to simulate another process winning the race
        if self == parent_dir and len(mkdir_calls) == 1:
            # Create the directory before the "real" mkdir attempt
            original_mkdir(self, parents=True, exist_ok=True)

        # Now call the original mkdir - this will fail with FileExistsError
        # if exist_ok=False, but succeed with exist_ok=True
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", tracking_mkdir):
        # This should NOT raise FileExistsError if exist_ok=True is used
        _ensure_parent_directory(target_path)

    # Verify the directory exists and mkdir was called
    assert parent_dir.exists()
    assert len(mkdir_calls) >= 1, "mkdir should have been called"

    # Verify exist_ok=True was used (the key fix)
    # The kwargs should have exist_ok=True
    mkdir_kwargs = mkdir_calls[0][2]
    assert mkdir_kwargs.get("exist_ok", False) is True, (
        "mkdir should use exist_ok=True to avoid TOCTOU race"
    )

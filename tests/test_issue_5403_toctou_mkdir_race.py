"""Regression tests for issue #5403: TOCTOU race condition in _ensure_parent_directory.

Issue: The check-then-mkdir pattern between exists() and mkdir(exist_ok=False)
creates a race condition window where another process could create the directory
between the check and the mkdir, causing FileExistsError.

The fix should make directory creation atomic by using exist_ok=True.

These tests verify the race condition is properly handled.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_handles_race_condition(tmp_path) -> None:
    """Test that _ensure_parent_directory handles race condition gracefully.

    This test simulates the race condition by mocking mkdir to first create
    the directory, then call the real mkdir (which would fail with exist_ok=False).
    The fix should use exist_ok=True so this doesn't raise FileExistsError.
    """
    # Create a unique test path in a non-existent directory
    test_dir = tmp_path / "race_test" / "subdir"
    test_file = test_dir / "todo.json"

    # Ensure the parent's parent exists for the test
    tmp_path.mkdir(parents=True, exist_ok=True)

    # Simulate the race condition: another process creates the directory
    # between our exists() check and mkdir() call
    original_mkdir = Path.mkdir

    def race_simulating_mkdir(self, *args, **kwargs):
        """Simulate race by creating directory before the actual mkdir call."""
        # First, simulate another process creating the directory
        if not self.exists():
            # Actually create the directory to simulate the race
            original_mkdir(self, parents=True, exist_ok=True)

        # Now call the real mkdir - with exist_ok=False, this would fail
        # But with the fix (exist_ok=True), it should succeed
        return original_mkdir(self, *args, **kwargs)

    # Patch Path.mkdir to simulate the race
    with patch.object(Path, 'mkdir', race_simulating_mkdir):
        # This should NOT raise FileExistsError after the fix
        _ensure_parent_directory(test_file)

    # Verify the directory now exists
    assert test_dir.exists()
    assert test_dir.is_dir()


def test_concurrent_directory_creation_no_race_condition(tmp_path) -> None:
    """Regression test for issue #5403: Race condition in concurrent directory creation.

    Tests that multiple processes calling save() on the same path with a non-existent
    parent directory should not raise FileExistsError. Each process should handle
    the case where the directory was created by another process.
    """
    # Create a unique test path in a non-existent directory
    db_path = tmp_path / "concurrent_dir_test" / "nested" / "db.json"

    def worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves to the same path, requiring directory creation."""
        try:
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)

            # Verify we can read back valid data
            loaded = storage.load()
            result_queue.put(("success", worker_id, len(loaded)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded without FileExistsError
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # Check for FileExistsError specifically - this indicates the race condition bug
    file_exists_errors = [r for r in errors if "FileExistsError" in str(r[2])]

    assert len(file_exists_errors) == 0, (
        f"Race condition detected: {len(file_exists_errors)} workers got FileExistsError. "
        f"Error details: {file_exists_errors}"
    )
    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}. "
        f"Errors: {errors}"
    )


def test_concurrent_ensure_parent_directory(tmp_path) -> None:
    """Test that concurrent calls to _ensure_parent_directory don't raise errors.

    This directly tests the race condition on directory creation.
    """
    test_dir = tmp_path / "concurrent_ensure" / "deeply" / "nested"
    test_file = test_dir / "todo.json"

    def worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that calls _ensure_parent_directory."""
        try:
            _ensure_parent_directory(test_file)
            result_queue.put(("success", worker_id, None))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # Check for FileExistsError specifically
    file_exists_errors = [r for r in errors if "FileExistsError" in str(r[2])]

    assert len(file_exists_errors) == 0, (
        f"Race condition detected: {len(file_exists_errors)} workers got FileExistsError. "
        f"Error details: {file_exists_errors}"
    )
    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}. Errors: {errors}"
    )

    # Verify directory exists
    assert test_dir.exists()
    assert test_dir.is_dir()

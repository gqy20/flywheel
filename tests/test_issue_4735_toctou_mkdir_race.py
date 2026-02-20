"""Regression tests for issue #4735: TOCTOU race condition in _ensure_parent_directory.

Issue: Race condition (TOCTOU) between parent directory validation and mkdir in _ensure_parent_directory

Location: src/flywheel/storage.py:35-50

Problem:
1. Lines 35-40: Iterates through parents checking exists()/is_dir() - race window for each path component
2. Lines 43-45: Second exists() check on parent before mkdir - another race window
3. exist_ok=False combined with pre-validation is contradictory and can fail if race occurs

Fix: Use exist_ok=True in mkdir() call and wrap the operation in try/except to handle
the case where another process creates/deletes directories concurrently.

Acceptance criteria:
- Concurrent directory creation by another process does not cause save() to fail
- File-as-directory validation still catches configuration errors
- All existing tests pass
"""

from __future__ import annotations

import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_concurrent_mkdir_race_condition_threaded(tmp_path) -> None:
    """Test that concurrent save() calls creating the same directory don't fail.

    This test demonstrates the TOCTOU race condition:
    1. Multiple threads check if directory exists (it doesn't)
    2. Multiple threads try to create the directory
    3. Only one succeeds in creating, others get FileExistsError
    4. With exist_ok=False, this causes unnecessary failures

    Expected behavior after fix: All threads should succeed gracefully.
    """
    # Use a shared parent directory that doesn't exist yet
    shared_db = tmp_path / "shared" / "deep" / "nested" / "todos.json"

    results = {"success": 0, "errors": []}
    lock = multiprocessing.Lock()

    def concurrent_save(worker_id: int) -> tuple[str, int, str | None]:
        """Worker that saves to same non-existent directory."""
        try:
            storage = TodoStorage(str(shared_db))
            todos = [Todo(id=1, text=f"worker-{worker_id}")]
            storage.save(todos)
            return ("success", worker_id, None)
        except Exception as e:
            return ("error", worker_id, str(e))

    # Run concurrent saves with threads
    num_workers = 10
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(concurrent_save, i) for i in range(num_workers)]
        for future in as_completed(futures):
            status, worker_id, error = future.result()
            with lock:
                if status == "success":
                    results["success"] += 1
                else:
                    results["errors"].append((worker_id, error))

    # All workers should succeed (no FileExistsError from mkdir race)
    assert len(results["errors"]) == 0, (
        f"Some workers failed due to race condition: {results['errors']}"
    )
    assert results["success"] == num_workers


def test_concurrent_mkdir_from_multiple_processes(tmp_path) -> None:
    """Regression test for issue #4735: Race condition in concurrent directory creation.

    Tests that multiple processes trying to create the same parent directory
    concurrently do not fail due to TOCTOU race condition.
    """
    db = tmp_path / "shared" / "data" / "todos.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that saves todos and reports success."""
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}-data")]
            storage.save(todos)
            result_queue.put(("success", worker_id, None))
        except FileExistsError as e:
            # This is the specific error we're trying to prevent
            result_queue.put(("file_exists_error", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently that all need to create the same directory
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    # Start all processes at roughly the same time to maximize race window
    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)

    # Start all processes
    for p in processes:
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # No worker should encounter FileExistsError (which indicates the race condition)
    file_exists_errors = [r for r in results if r[0] == "file_exists_error"]
    assert len(file_exists_errors) == 0, (
        f"Workers hit FileExistsError due to race condition: {file_exists_errors}"
    )

    # All workers should succeed
    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}. Errors: {results}"
    )


def test_ensure_parent_directory_with_exist_ok_true(tmp_path) -> None:
    """Test that _ensure_parent_directory handles concurrent directory creation.

    Before fix: exist_ok=False causes FileExistsError when another process
    creates the directory between the exists() check and mkdir().

    After fix: exist_ok=True should make this race-safe.
    """
    # Directory that doesn't exist yet
    target = tmp_path / "concurrent" / "deep" / "file.json"

    # First call should create the directory
    _ensure_parent_directory(target)
    assert target.parent.exists()
    assert target.parent.is_dir()

    # Second call should succeed (not fail with FileExistsError)
    # This simulates the race where another process created the directory
    _ensure_parent_directory(target)  # Should not raise


def test_file_as_directory_validation_still_works(tmp_path) -> None:
    """Regression test: file-as-directory validation should still work after fix.

    Ensures that the fix doesn't break the important validation that catches
    configuration errors when a path component is a file instead of directory.
    """
    # Create a file where we expect a directory
    blocking_file = tmp_path / "blocking.txt"
    blocking_file.write_text("I am a file")

    # Try to create a path that would need this file to be a directory
    invalid_path = blocking_file / "subdir" / "todo.json"

    # Should raise ValueError about file vs directory
    with pytest.raises(ValueError, match=r"(file|directory|not a directory)"):
        _ensure_parent_directory(invalid_path)


def test_ensure_parent_directory_creates_nested_structure(tmp_path) -> None:
    """Test that _ensure_parent_directory correctly creates nested directories."""
    # Deep path that doesn't exist
    deep_path = tmp_path / "a" / "b" / "c" / "d" / "file.json"

    # Should create all parent directories
    _ensure_parent_directory(deep_path)

    # Verify all directories were created
    assert (tmp_path / "a").is_dir()
    assert (tmp_path / "a" / "b").is_dir()
    assert (tmp_path / "a" / "b" / "c").is_dir()
    assert (tmp_path / "a" / "b" / "c" / "d").is_dir()

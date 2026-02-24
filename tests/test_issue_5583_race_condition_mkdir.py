"""Regression tests for issue #5583: Race condition in _ensure_parent_directory.

Issue: exist_ok=False can raise FileExistsError if directory is created
concurrently between the exists() check and mkdir() call (TOCTOU race condition).

These tests verify that concurrent saves to the same non-existent parent directory
do not fail with FileExistsError.
"""

from __future__ import annotations

import concurrent.futures
import tempfile
from pathlib import Path

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_concurrent_save_to_same_new_directory_succeeds() -> None:
    """Issue #5583: Concurrent saves to same non-existent directory should not raise FileExistsError.

    Before fix: Race condition between exists() check and mkdir(exist_ok=False) causes
    one process to raise FileExistsError when directory is created by another process.

    After fix: Using exist_ok=True makes the operation idempotent, preventing the race.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Both storage instances point to the same non-existent parent directory
        base_path = Path(tmpdir) / "new_subdir" / "nested" / "todo.json"
        assert not base_path.parent.exists(), "Parent should not exist at start"

        storage1 = TodoStorage(str(base_path))
        storage2 = TodoStorage(str(base_path))

        # Define a function that saves data using Todo objects
        def save_with_storage(storage: TodoStorage, data_id: int) -> str:
            storage.save([Todo(id=data_id, text=f"task {data_id}", done=False)])
            return "success"

        # Run concurrent saves - this should NOT raise FileExistsError
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(save_with_storage, storage1, i) for i in range(10)
            ] + [
                executor.submit(save_with_storage, storage2, i) for i in range(10, 20)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All saves should succeed
        assert len(results) == 20
        assert all(r == "success" for r in results)


def test_ensure_parent_directory_with_concurrent_mkdir() -> None:
    """Issue #5583: _ensure_parent_directory should handle concurrent mkdir gracefully.

    This directly tests the race condition by calling mkdir concurrently.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        target_path = Path(tmpdir) / "concurrent" / "deep" / "file.json"
        assert not target_path.parent.exists()

        def ensure_dir() -> None:
            _ensure_parent_directory(target_path)

        # Run multiple concurrent _ensure_parent_directory calls
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(ensure_dir) for _ in range(20)]
            # This should NOT raise any exceptions
            for future in concurrent.futures.as_completed(futures):
                future.result()  # Will raise if any call failed

        # Directory should exist after all calls
        assert target_path.parent.exists()
        assert target_path.parent.is_dir()


def test_concurrent_ensure_parent_directory_high_contention() -> None:
    """Issue #5583: High contention scenario with many threads.

    Simulates many processes trying to create the same directory simultaneously.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        target_path = Path(tmpdir) / "high_contention" / "path" / "data.json"

        # Use barrier to maximize contention
        import threading

        barrier = threading.Barrier(50)
        errors: list[Exception] = []

        def ensure_dir_with_barrier() -> None:
            barrier.wait()  # Synchronize all threads
            try:
                _ensure_parent_directory(target_path)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=ensure_dir_with_barrier) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should have occurred
        assert len(errors) == 0, f"Got errors: {errors}"
        assert target_path.parent.exists()

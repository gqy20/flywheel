"""Regression tests for issue #3226: TOCTOU race condition in _ensure_parent_directory.

Issue: There is a Time-of-Check-Time-of-Use race condition between:
1. if not parent.exists():  # Check if parent exists
2. parent.mkdir(parents=True, exist_ok=False)  # Create directory

Between these two operations, another process could create the directory,
causing mkdir to fail with FileExistsError even though the directory now exists.

The fix should use exist_ok=True and distinguish between:
- Directory already exists (race condition - should succeed)
- Path component is a file (configuration error - should raise ValueError)

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import contextlib
import multiprocessing
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


class TestTOCTOURaceCondition:
    """Tests for TOCTOU race condition in _ensure_parent_directory."""

    def test_concurrent_directory_creation_succeeds(self, tmp_path) -> None:
        """Issue #3226: Multiple processes creating same parent directory should all succeed.

        This test simulates the TOCTOU race condition where multiple processes
        try to create the same parent directory concurrently. Before the fix,
        some processes would fail with FileExistsError/OSError. After the fix,
        all processes should succeed.
        """
        db_path = tmp_path / "shared" / "todos.json"
        num_threads = 10
        results = []
        errors = []

        def save_todos(worker_id: int) -> None:
            """Worker that creates todos, triggering directory creation."""
            try:
                storage = TodoStorage(str(db_path))
                todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
                storage.save(todos)
                results.append(worker_id)
            except Exception as e:
                errors.append((worker_id, str(e)))

        # Use threads for faster execution in test
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=save_todos, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=10)

        # All workers should succeed (no race condition errors)
        assert len(errors) == 0, f"Workers encountered errors: {errors}"
        assert len(results) == num_threads, f"Expected {num_threads} successes, got {len(results)}"

    def test_ensure_parent_directory_handles_race_condition(self, tmp_path) -> None:
        """Issue #3226: _ensure_parent_directory should handle race condition gracefully.

        This directly tests the _ensure_parent_directory function by simulating
        what happens when another process creates the directory between the
        exists() check and the mkdir() call.
        """
        target_path = tmp_path / "race" / "test.json"
        results = {"success": 0, "errors": []}

        def create_directory_during_race() -> None:
            """Simulate another process creating the directory."""
            time.sleep(0.001)  # Small delay to increase race likelihood
            with contextlib.suppress(FileExistsError):
                target_path.parent.mkdir(parents=True, exist_ok=True)

        # Run multiple threads calling _ensure_parent_directory concurrently
        def ensure_parent() -> None:
            try:
                _ensure_parent_directory(target_path)
                results["success"] += 1
            except Exception as e:
                results["errors"].append(str(e))

        threads = []
        for _ in range(10):
            # Start directory creator
            t1 = threading.Thread(target=create_directory_during_race)
            t2 = threading.Thread(target=ensure_parent)
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        for t in threads:
            t.join(timeout=10)

        # All calls should succeed
        assert len(results["errors"]) == 0, f"Errors: {results['errors']}"

    def test_file_as_parent_still_raises_valueerror(self, tmp_path) -> None:
        """Issue #3226: Fix should not affect file-as-directory error detection.

        Even with exist_ok=True, the code should still detect when a path
        component is a file instead of a directory and raise ValueError.
        """
        # Create a file where we need a directory
        blocking_file = tmp_path / "blocking.txt"
        blocking_file.write_text("I am a file")

        # Try to create a path that needs the file to be a directory
        target_path = blocking_file / "subdir" / "test.json"

        # Should raise ValueError for file-as-directory, not succeed silently
        with pytest.raises(ValueError, match=r"(file|not a directory|exists as a file)"):
            _ensure_parent_directory(target_path)

    def test_multiprocess_concurrent_save_succeeds(self, tmp_path) -> None:
        """Issue #3226: Multiple processes saving concurrently should all succeed.

        This is a more realistic test using multiprocessing instead of threads,
        simulating actual concurrent process behavior.
        """

        def save_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
            """Worker that saves todos."""
            try:
                storage = TodoStorage(db_path)
                todos = [Todo(id=worker_id, text=f"todo-{worker_id}")]
                storage.save(todos)
                result_queue.put(("success", worker_id))
            except Exception as e:
                result_queue.put(("error", worker_id, str(e)))

        db_path = tmp_path / "multi" / "todos.json"
        num_workers = 5
        result_queue = multiprocessing.Queue()
        processes = []

        for i in range(num_workers):
            p = multiprocessing.Process(
                target=save_worker,
                args=(i, str(db_path), result_queue)
            )
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=10)

        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        successes = [r for r in results if r[0] == "success"]
        errors = [r for r in results if r[0] == "error"]

        assert len(errors) == 0, f"Process errors: {errors}"
        assert len(successes) == num_workers

    def test_normal_directory_creation_still_works(self, tmp_path) -> None:
        """Issue #3226: Normal nested directory creation should still work after fix."""
        target_path = tmp_path / "a" / "b" / "c" / "test.json"

        # Should succeed in creating nested directories
        _ensure_parent_directory(target_path)

        # Verify directory was created
        assert target_path.parent.exists()
        assert target_path.parent.is_dir()

    def test_existing_directory_succeeds(self, tmp_path) -> None:
        """Issue #3226: Calling with existing directory should succeed."""
        target_path = tmp_path / "existing" / "test.json"

        # Pre-create the directory
        target_path.parent.mkdir(parents=True)

        # Should succeed without error
        _ensure_parent_directory(target_path)

        assert target_path.parent.exists()

    def test_simulated_toctou_race_condition(self, tmp_path) -> None:
        """Issue #3226: Simulate TOCTOU race condition by mocking mkdir to raise FileExistsError.

        This test directly simulates what happens when another process creates
        the directory between exists() check and mkdir() call. Before the fix,
        this would raise an OSError. After the fix, it should succeed silently.
        """
        target_path = tmp_path / "race" / "test.json"
        original_mkdir = Path.mkdir

        def mkdir_with_race_condition(self, *args, **kwargs):
            """Mock mkdir that simulates another process creating the directory first."""
            # If this is the first call (no exist_ok behavior), simulate race condition
            if not kwargs.get('exist_ok', False):
                # Create the directory to simulate another process creating it
                original_mkdir(self, parents=True, exist_ok=True)
                # Now raise FileExistsError as if it was a race condition
                raise FileExistsError(f"[Errno 17] File exists: '{self}'")
            else:
                # With exist_ok=True, this should succeed
                return original_mkdir(self, *args, **kwargs)

        # Test with mocked mkdir that simulates the race condition
        with patch.object(Path, 'mkdir', mkdir_with_race_condition):
            # This should NOT raise an error - the fix should handle FileExistsError
            _ensure_parent_directory(target_path)

        # Verify the directory now exists
        assert target_path.parent.exists()

    def test_simulated_toctou_with_storage_save(self, tmp_path) -> None:
        """Issue #3226: Simulate TOCTOU race condition during TodoStorage.save().

        This tests the race condition in the context of save() which calls
        _ensure_parent_directory.
        """
        db_path = tmp_path / "race" / "todos.json"
        original_mkdir = Path.mkdir
        call_count = [0]

        def mkdir_with_race_condition(self, *args, **kwargs):
            """Mock mkdir that simulates race condition on first call."""
            call_count[0] += 1
            # On first call, simulate race condition
            if call_count[0] == 1 and not kwargs.get('exist_ok', False):
                # Create the directory to simulate another process creating it
                original_mkdir(self, parents=True, exist_ok=True)
                raise FileExistsError(f"[Errno 17] File exists: '{self}'")
            else:
                # Subsequent calls or exist_ok=True should work normally
                return original_mkdir(self, *args, **kwargs)

        storage = TodoStorage(str(db_path))
        todos = [Todo(id=1, text="test")]

        with patch.object(Path, 'mkdir', mkdir_with_race_condition):
            # This should succeed, not raise OSError
            storage.save(todos)

        # Verify data was saved
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

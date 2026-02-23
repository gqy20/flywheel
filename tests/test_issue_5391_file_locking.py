"""Tests for file lock mechanism for safe concurrent multi-process writes.

This test suite verifies that TodoStorage.save() uses file locking
to prevent race conditions when multiple processes write to the same file.

Issue: #5391
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestFileLockingBackwardCompatibility:
    """Test backward compatibility - use_locking parameter."""

    def test_default_use_locking_is_true(self, tmp_path: Path) -> None:
        """Test that file locking is enabled by default."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        assert storage.use_locking is True

    def test_can_disable_locking_explicitly(self, tmp_path: Path) -> None:
        """Test that file locking can be disabled explicitly."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_locking=False)
        assert storage.use_locking is False

    def test_save_works_without_locking_when_disabled(self, tmp_path: Path) -> None:
        """Test that save() works correctly when locking is disabled."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_locking=False)

        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"


class TestFileLockingLockRelease:
    """Test that lock is released properly."""

    def test_lock_released_after_successful_write(self, tmp_path: Path) -> None:
        """Test that lock is released after a successful write."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_locking=True)

        todos = [Todo(id=1, text="first")]
        storage.save(todos)

        # Should be able to save again immediately (lock was released)
        todos2 = [Todo(id=2, text="second")]
        storage.save(todos2)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "second"

    def test_lock_released_after_exception_during_write(self, tmp_path: Path) -> None:
        """Test that lock is released even if write operation fails."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_locking=True)

        # Create initial data
        initial_todos = [Todo(id=1, text="initial")]
        storage.save(initial_todos)

        # Simulate a write failure
        import tempfile

        def failing_mkstemp(*args, **kwargs):
            raise OSError("Simulated write failure")

        with (
            patch.object(tempfile, "mkstemp", failing_mkstemp),
            pytest.raises(OSError, match="Simulated write failure"),
        ):
            storage.save([Todo(id=2, text="should fail")])

        # Lock should be released, and we should be able to write again
        storage.save([Todo(id=3, text="after failure")])

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "after failure"


class TestFileLockingConcurrency:
    """Test concurrent writes with file locking."""

    def test_concurrent_writes_are_serialized(self, tmp_path: Path) -> None:
        """Test that two concurrent save() calls result in serialized writes.

        With file locking enabled, concurrent writes should be serialized
        (no interleaving), and the final file should contain valid data
        from one of the writers.
        """
        db = tmp_path / "concurrent.json"

        # Barrier to synchronize workers
        barrier = multiprocessing.Barrier(2)
        result_queue = multiprocessing.Queue()

        def save_worker(worker_id: int) -> None:
            """Worker function that saves todos with file locking."""
            try:
                storage = TodoStorage(str(db), use_locking=True)

                # Wait for both workers to be ready
                barrier.wait(timeout=5)

                # Each worker writes multiple times
                for i in range(3):
                    todos = [
                        Todo(id=i, text=f"worker-{worker_id}-batch-{i}"),
                    ]
                    storage.save(todos)
                    time.sleep(0.001)  # Small delay to increase contention

                result_queue.put(("success", worker_id))
            except Exception as e:
                result_queue.put(("error", worker_id, str(e)))

        # Run two workers concurrently
        p1 = multiprocessing.Process(target=save_worker, args=(1,))
        p2 = multiprocessing.Process(target=save_worker, args=(2,))

        p1.start()
        p2.start()

        p1.join(timeout=15)
        p2.join(timeout=15)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        successes = [r for r in results if r[0] == "success"]
        errors = [r for r in results if r[0] == "error"]

        # All workers should succeed
        assert len(errors) == 0, f"Workers encountered errors: {errors}"
        assert len(successes) == 2, f"Expected 2 successes, got {len(successes)}"

        # Final file should contain valid JSON (not corrupted)
        storage = TodoStorage(str(db))
        final_todos = storage.load()

        # Should have valid data from one of the workers
        assert len(final_todos) >= 1
        for todo in final_todos:
            assert isinstance(todo.text, str)
            assert todo.text.startswith("worker-")

    def test_multiprocess_no_data_corruption_with_locking(
        self, tmp_path: Path
    ) -> None:
        """Test that multiple processes writing with locking produce valid JSON.

        This is a stronger version of test_concurrent_save_from_multiple_processes
        that verifies the locking mechanism prevents race conditions.
        """
        db = tmp_path / "multi.json"
        num_workers = 5
        num_writes_per_worker = 5

        result_queue = multiprocessing.Queue()

        def save_worker(worker_id: int) -> None:
            """Worker that performs multiple writes with locking."""
            try:
                storage = TodoStorage(str(db), use_locking=True)

                for i in range(num_writes_per_worker):
                    todos = [
                        Todo(
                            id=worker_id * 100 + i,
                            text=f"worker-{worker_id}-write-{i}",
                        )
                    ]
                    storage.save(todos)
                    time.sleep(0.001)

                result_queue.put(("success", worker_id))
            except Exception as e:
                result_queue.put(("error", worker_id, str(e)))

        processes = [
            multiprocessing.Process(target=save_worker, args=(i,))
            for i in range(num_workers)
        ]

        for p in processes:
            p.start()

        for p in processes:
            p.join(timeout=20)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        successes = [r for r in results if r[0] == "success"]
        errors = [r for r in results if r[0] == "error"]

        # All workers should succeed
        assert len(errors) == 0, f"Workers encountered errors: {errors}"
        assert len(successes) == num_workers

        # Verify final file is valid JSON
        storage = TodoStorage(str(db))
        final_todos = storage.load()
        assert isinstance(final_todos, list)

        # Verify data integrity
        for todo in final_todos:
            assert hasattr(todo, "id")
            assert hasattr(todo, "text")
            assert isinstance(todo.text, str)


class TestFileLockingCrossPlatform:
    """Test cross-platform file locking support."""

    def test_locking_works_on_current_platform(self, tmp_path: Path) -> None:
        """Test that file locking works on the current platform."""
        db = tmp_path / "platform.json"
        storage = TodoStorage(str(db), use_locking=True)

        # Should not raise any exceptions
        storage.save([Todo(id=1, text="platform test")])

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "platform test"

    def test_locking_context_manager_behavior(self, tmp_path: Path) -> None:
        """Test that _acquire_lock works as a context manager."""
        db = tmp_path / "context.json"
        storage = TodoStorage(str(db), use_locking=True)

        # Test that we can use the lock context manager directly
        with storage._acquire_lock():
            # Inside the lock, we should be able to perform operations
            # Note: we don't call save() here as it would try to re-acquire the lock
            pass

        # After the context exits, the lock should be released
        # and we should be able to save
        storage.save([Todo(id=1, text="test")])

        loaded = storage.load()
        assert loaded[0].text == "test"

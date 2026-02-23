"""Tests for file lock mechanism in TodoStorage.

This test suite verifies that TodoStorage supports optional file locking
for safe concurrent multi-process writes, preventing data corruption
when multiple TodoApp instances write to the same JSON file simultaneously.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestFileLockingFeature:
    """Tests for the file locking feature in TodoStorage."""

    def test_use_locking_parameter_exists(self) -> None:
        """Test that TodoStorage accepts use_locking constructor parameter."""
        # Should be able to create storage with locking enabled
        storage_with_lock = TodoStorage(path="test.json", use_locking=True)
        assert storage_with_lock.use_locking is True

        # Should be able to create storage with locking disabled (default)
        storage_without_lock = TodoStorage(path="test.json", use_locking=False)
        assert storage_without_lock.use_locking is False

        # Default should be False for backward compatibility
        storage_default = TodoStorage(path="test.json")
        assert storage_default.use_locking is False

    def test_lock_released_after_exception_during_write(self, tmp_path: Path) -> None:
        """Test that lock is released even if write operation fails."""
        db = tmp_path / "locked.json"
        storage = TodoStorage(str(db), use_locking=True)

        # Create initial data
        original_todos = [Todo(id=1, text="original")]
        storage.save(original_todos)

        # Simulate write failure during save with locking
        def failing_mkstemp(*args, **kwargs):
            raise OSError("Simulated write failure")

        import tempfile

        with (
            patch.object(tempfile, "mkstemp", failing_mkstemp),
            pytest.raises(OSError, match="Simulated write failure"),
        ):
            storage.save([Todo(id=2, text="new")])

        # Lock should be released, so another save should work
        storage.save([Todo(id=3, text="after failure")])

        # Verify the final save succeeded
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "after failure"

    def test_backward_compatibility_without_locking(self, tmp_path: Path) -> None:
        """Test that save() works without locking when use_locking=False."""
        db = tmp_path / "nolock.json"
        storage = TodoStorage(str(db), use_locking=False)

        # Should work normally without any locking
        todos = [Todo(id=1, text="test"), Todo(id=2, text="another")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "test"
        assert loaded[1].text == "another"

    def test_concurrent_saves_with_locking_are_serialized(self, tmp_path: Path) -> None:
        """Test that concurrent saves with locking are serialized.

        When two processes save to the same file with locking enabled,
        the writes should be serialized (no interleaving) and both
        should complete without data loss.
        """
        db = tmp_path / "concurrent_locked.json"

        def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
            """Worker function that saves todos with locking enabled."""
            try:
                storage = TodoStorage(str(db), use_locking=True)
                # Each worker creates unique todos
                todos = [
                    Todo(id=worker_id * 10 + i, text=f"worker-{worker_id}-todo-{i}")
                    for i in range(5)
                ]
                storage.save(todos)

                # Verify we can read back valid data
                loaded = storage.load()
                result_queue.put(("success", worker_id, len(loaded)))
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

        # Wait for all processes to complete
        for p in processes:
            p.join(timeout=30)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # All workers should have succeeded
        successes = [r for r in results if r[0] == "success"]
        errors = [r for r in results if r[0] == "error"]

        assert len(errors) == 0, f"Workers encountered errors: {errors}"
        assert len(successes) == num_workers, (
            f"Expected {num_workers} successes, got {len(successes)}"
        )

        # Final verification: file should contain valid JSON
        storage = TodoStorage(str(db))
        final_todos = storage.load()
        assert isinstance(final_todos, list)
        # Should have exactly 5 todos from the last writer
        assert len(final_todos) == 5


class TestFileLockCrossPlatform:
    """Tests for cross-platform file locking support."""

    def test_locking_works_on_current_platform(self, tmp_path: Path) -> None:
        """Test that file locking works on the current platform."""
        db = tmp_path / "platform_test.json"
        storage = TodoStorage(str(db), use_locking=True)

        todos = [Todo(id=1, text="platform test")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "platform test"

    def test_locking_context_manager_exists(self) -> None:
        """Test that _acquire_lock context manager exists and works."""
        storage = TodoStorage(path="test.json", use_locking=True)

        # Should have the _acquire_lock method
        assert hasattr(storage, "_acquire_lock")

        # The method should be callable and return a context manager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "lock_test.json"
            storage = TodoStorage(str(db_path), use_locking=True)

            # Create the file first
            db_path.write_text("[]")

            # Using the context manager should work
            with storage._acquire_lock():
                # Should be able to perform operations while holding lock
                pass

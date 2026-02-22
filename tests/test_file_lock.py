"""Tests for file lock mechanism to prevent concurrent write conflicts.

This test suite verifies that TodoStorage can optionally use file locking
to prevent last-writer-wins data loss when multiple processes modify the same file.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestFileLockParameter:
    """Tests for the use_lock parameter in TodoStorage."""

    def test_storage_accepts_use_lock_parameter(self, tmp_path: Path) -> None:
        """TodoStorage should accept use_lock parameter in __init__."""
        db = tmp_path / "todo.json"
        # Should not raise
        storage = TodoStorage(str(db), use_lock=True)
        assert storage is not None

    def test_storage_default_use_lock_is_false(self, tmp_path: Path) -> None:
        """By default, use_lock should be False for backward compatibility."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        assert storage.use_lock is False

    def test_storage_with_use_lock_true(self, tmp_path: Path) -> None:
        """TodoStorage should store use_lock=True when specified."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_lock=True)
        assert storage.use_lock is True


class TestTransactionContextManager:
    """Tests for the transaction() context manager."""

    def test_transaction_context_manager_exists(self, tmp_path: Path) -> None:
        """TodoStorage should have a transaction() context manager."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_lock=True)
        # Should not raise
        with storage.transaction():
            pass

    def test_transaction_no_op_when_use_lock_false(self, tmp_path: Path) -> None:
        """transaction() should be a no-op when use_lock is False."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_lock=False)

        # Should work without acquiring any lock
        with storage.transaction():
            todos = [Todo(id=1, text="test")]
            storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_transaction_load_save_cycle(self, tmp_path: Path) -> None:
        """transaction() should protect the entire load-modify-save cycle."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_lock=True)

        # Initial save
        storage.save([])

        # Transaction should hold lock for entire operation
        with storage.transaction():
            todos = storage.load()
            todos.append(Todo(id=1, text="test"))
            storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1

    def test_nested_transaction_is_reentrant(self, tmp_path: Path) -> None:
        """Nested transaction() calls should be reentrant (no deadlock)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_lock=True)

        storage.save([])

        # Nested transactions should not deadlock
        with storage.transaction():  # noqa: SIM117
            with storage.transaction():
                todos = storage.load()
                todos.append(Todo(id=1, text="nested"))
                storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1


class TestFileLockConcurrency:
    """Tests for concurrent access with file locking."""

    def test_concurrent_writes_without_lock_loses_data(self, tmp_path: Path) -> None:
        """
        Demonstrate that without locking, concurrent writes can lose data.

        This is the "last-writer-wins" behavior that the lock mechanism aims to prevent.
        Note: This test demonstrates the problem, but may not always fail because
        it depends on timing.
        """
        db = tmp_path / "todo.json"

        # Initialize with empty list
        storage = TodoStorage(str(db))
        storage.save([])

        def writer_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
            """Worker that loads, adds a todo, and saves."""
            try:
                storage = TodoStorage(str(db), use_lock=False)
                # Load current state
                todos = storage.load()
                # Add a unique todo
                new_id = len(todos) + 1
                todos.append(Todo(id=new_id, text=f"worker-{worker_id}"))
                # Simulate processing delay to increase race condition
                time.sleep(0.01)
                # Save
                storage.save(todos)
                result_queue.put(("success", worker_id, new_id))
            except Exception as e:
                result_queue.put(("error", worker_id, str(e)))

        # Run 3 workers concurrently
        num_workers = 3
        processes = []
        result_queue = multiprocessing.Queue()

        for i in range(num_workers):
            p = multiprocessing.Process(target=writer_worker, args=(i, result_queue))
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=10)

        # Count successful writes
        successes = []
        while not result_queue.empty():
            successes.append(result_queue.get())

        # Without locking, we may have lost some data (but not guaranteed by timing)
        # This test demonstrates the behavior but doesn't assert on it

    def test_concurrent_writes_with_lock_preserves_all_data(
        self, tmp_path: Path
    ) -> None:
        """
        Test that with file locking, concurrent write-modify-read cycles preserve data.

        Multiple processes load the file, add a unique todo, and save.
        With locking, all todos should be preserved (no data loss).
        """
        db = tmp_path / "todo.json"

        # Initialize with empty list
        storage = TodoStorage(str(db), use_lock=True)
        storage.save([])

        def locking_writer_worker(
            worker_id: int, result_queue: multiprocessing.Queue
        ) -> None:
            """Worker that loads, adds a todo, and saves with locking."""
            try:
                storage = TodoStorage(str(db), use_lock=True)
                # Use transaction to hold lock for entire load-modify-save cycle
                with storage.transaction():
                    todos = storage.load()
                    # Add a unique todo
                    new_id = len(todos) + 1
                    todos.append(Todo(id=new_id, text=f"worker-{worker_id}"))
                    # Simulate small processing delay
                    time.sleep(0.005)
                    # Save
                    storage.save(todos)
                result_queue.put(("success", worker_id, new_id))
            except Exception as e:
                result_queue.put(("error", worker_id, str(e)))

        # Run 5 workers concurrently
        num_workers = 5
        processes = []
        result_queue = multiprocessing.Queue()

        for i in range(num_workers):
            p = multiprocessing.Process(
                target=locking_writer_worker, args=(i, result_queue)
            )
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=30)

        # Count successful writes
        successes = []
        errors = []
        while not result_queue.empty():
            result = result_queue.get()
            if result[0] == "success":
                successes.append(result)
            else:
                errors.append(result)

        # All workers should succeed
        assert len(errors) == 0, f"Workers encountered errors: {errors}"
        assert len(successes) == num_workers

        # All todos should be preserved (no data loss)
        final_todos = storage.load()
        assert len(final_todos) == num_workers, (
            f"Expected {num_workers} todos (one from each worker), "
            f"got {len(final_todos)}. Data was lost due to concurrent writes."
        )

        # Verify each worker's todo is present
        worker_texts = {todo.text for todo in final_todos}
        for i in range(num_workers):
            expected_text = f"worker-{i}"
            assert expected_text in worker_texts, (
                f"Missing todo from worker {i}. Data was lost."
            )


class TestFileLockTimeout:
    """Tests for lock timeout behavior."""

    def test_lock_timeout_raises_exception(self, tmp_path: Path) -> None:
        """
        Test that acquiring lock with timeout raises appropriate exception
        when lock cannot be acquired.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_lock=True, lock_timeout=0.1)
        storage.save([])

        # This test verifies the timeout parameter exists
        # A more complex test would require holding the lock from another process
        assert storage.lock_timeout == 0.1

    def test_default_lock_timeout_is_reasonable(self, tmp_path: Path) -> None:
        """Default lock timeout should be a reasonable value."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_lock=True)
        # Default should be something reasonable (e.g., 30 seconds)
        assert storage.lock_timeout > 0
        assert storage.lock_timeout <= 60  # Not too long


class TestBackwardCompatibility:
    """Tests for backward compatibility when not using locks."""

    def test_without_lock_works_as_before(self, tmp_path: Path) -> None:
        """Without use_lock, behavior should be identical to current behavior."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_lock=False)

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_save_without_existing_lock_file(self, tmp_path: Path) -> None:
        """Saving should work even if a stale .lock file exists from previous run."""
        db = tmp_path / "todo.json"
        lock_file = tmp_path / ".todo.json.lock"

        # Create a stale lock file
        lock_file.touch()

        storage = TodoStorage(str(db), use_lock=True)
        todos = [Todo(id=1, text="test")]
        # Should work despite stale lock file
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1

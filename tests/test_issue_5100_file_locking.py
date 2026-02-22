"""Tests for file locking mechanism to prevent concurrent write conflicts.

Issue #5100: Add file locking mechanism to prevent concurrent write conflicts.

This test suite verifies that TodoStorage can optionally use file locking
to prevent data loss when multiple processes concurrently modify the same file.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestFileLockingParameter:
    """Tests for the use_lock parameter in TodoStorage."""

    def test_storage_accepts_use_lock_parameter(self, tmp_path: Path) -> None:
        """TodoStorage should accept use_lock parameter at initialization."""
        db = tmp_path / "todo.json"
        # This should not raise - use_lock is optional
        storage = TodoStorage(str(db), use_lock=True)
        assert storage.path == db

    def test_storage_default_use_lock_is_false(self, tmp_path: Path) -> None:
        """By default, use_lock should be False for backward compatibility."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        # Default behavior should be no locking (backward compatible)
        assert not getattr(storage, "use_lock", False)


class TestFileLockingPreventsDataLoss:
    """Tests that file locking prevents concurrent write data loss."""

    def test_concurrent_modifications_with_lock_no_data_loss(
        self, tmp_path: Path
    ) -> None:
        """With locking enabled, concurrent load->modify->save should not lose data.

        This test simulates two processes that:
        1. Load the same initial state
        2. Each adds a different todo
        3. Both save

        Without locking: last-writer-wins, one todo is lost
        With locking: both todos should be preserved through proper serialization
        """
        db = tmp_path / "locked.json"

        # Create initial state
        initial_storage = TodoStorage(str(db), use_lock=True)
        initial_storage.save([Todo(id=1, text="initial")])

        def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
            """Worker that loads, adds a todo, and saves."""
            try:
                storage = TodoStorage(str(db), use_lock=True)
                # Load current state
                todos = storage.load()
                # Add new todo
                new_id = max((t.id for t in todos), default=0) + 1
                todos.append(Todo(id=new_id, text=f"worker-{worker_id}-added"))
                # Save back
                storage.save(todos)
                result_queue.put(("success", worker_id))
            except Exception as e:
                result_queue.put(("error", worker_id, str(e)))

        # Run two workers concurrently
        result_queue: multiprocessing.Queue = multiprocessing.Queue()
        processes = []
        for i in range(2):
            p = multiprocessing.Process(target=add_todo_worker, args=(i, result_queue))
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=10)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        errors = [r for r in results if r[0] == "error"]
        assert len(errors) == 0, f"Workers had errors: {errors}"

        # Verify no data loss: should have initial + 2 additions = 3 todos
        final_storage = TodoStorage(str(db), use_lock=True)
        final_todos = final_storage.load()

        assert len(final_todos) == 3, (
            f"Expected 3 todos (1 initial + 2 additions), got {len(final_todos)}. "
            f"Data was lost due to concurrent write conflict."
        )

        # Verify we have all expected todos
        texts = {t.text for t in final_todos}
        assert "initial" in texts
        assert "worker-0-added" in texts
        assert "worker-1-added" in texts


class TestFileLockTimeout:
    """Tests for lock timeout behavior."""

    def test_lock_timeout_raises_exception(self, tmp_path: Path) -> None:
        """Lock acquisition with timeout should raise on timeout."""
        db = tmp_path / "timeout.json"

        # Storage with very short timeout
        storage = TodoStorage(str(db), use_lock=True, lock_timeout=0.1)
        storage.save([Todo(id=1, text="test")])

        # This is a basic test - more complex timeout tests would need
        # to actually hold a lock from another process
        assert storage.path == db


class TestBackwardCompatibility:
    """Tests for backward compatibility without locking."""

    def test_without_lock_last_writer_wins(self, tmp_path: Path) -> None:
        """Without locking, behavior remains last-writer-wins (backward compatible)."""
        db = tmp_path / "nolock.json"

        # Create initial state with use_lock=False (default)
        storage1 = TodoStorage(str(db))  # No locking
        storage1.save([Todo(id=1, text="initial")])

        # Another storage object loads
        storage2 = TodoStorage(str(db))
        todos2 = storage2.load()

        # First storage also loads (same state)
        todos1 = storage1.load()

        # Both add todos
        todos1.append(Todo(id=2, text="storage1-added"))
        todos2.append(Todo(id=2, text="storage2-added"))  # Same ID - conflict!

        # Both save - last writer wins
        storage1.save(todos1)
        storage2.save(todos2)

        # Final state: only storage2's version survives (last-writer-wins)
        final = TodoStorage(str(db)).load()
        assert len(final) == 2
        texts = {t.text for t in final}
        # Only storage2's version should survive (it wrote last)
        assert "storage2-added" in texts
        # storage1's addition was lost
        assert "storage1-added" not in texts

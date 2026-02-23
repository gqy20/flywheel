"""Tests for file-based locking in TodoStorage.

This test suite verifies that TodoStorage uses file-based locking
to protect against race conditions when multiple processes access
the same JSON file concurrently.

Issue: #5405
"""

from __future__ import annotations

import json
import multiprocessing
import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestFileLockingUnit:
    """Unit tests verifying lock acquisition in load() and save()."""

    def test_load_acquires_shared_lock(self, tmp_path: Path) -> None:
        """Test that load() acquires a shared lock before reading."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text="test")])

        # Track lock calls
        lock_calls = []

        def mock_flock(fd, operation):
            lock_calls.append(("flock", fd, operation))
            # Don't actually lock, just record the call
            return 0

        # flock is imported in storage module
        import fcntl

        with patch.object(fcntl, "flock", mock_flock):
            storage.load()

        # Verify lock was called with LOCK_SH (shared lock)
        assert any(call[2] == fcntl.LOCK_SH for call in lock_calls), (
            f"Expected LOCK_SH call, got: {lock_calls}"
        )

    def test_save_acquires_exclusive_lock(self, tmp_path: Path) -> None:
        """Test that save() acquires an exclusive lock before writing."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Track lock calls
        lock_calls = []

        def mock_flock(fd, operation):
            lock_calls.append(("flock", fd, operation))
            # Don't actually lock, just record the call
            return 0

        import fcntl

        with patch.object(fcntl, "flock", mock_flock):
            storage.save([Todo(id=1, text="test")])

        # Verify lock was called with LOCK_EX (exclusive lock)
        assert any(call[2] == fcntl.LOCK_EX for call in lock_calls), (
            f"Expected LOCK_EX call, got: {lock_calls}"
        )


class TestFileLockingIntegration:
    """Integration tests for file locking behavior."""

    def test_concurrent_read_write_no_data_loss(self, tmp_path: Path) -> None:
        """Test that concurrent read/write operations don't cause data loss.

        This test verifies that:
        1. A reader never sees partial/corrupted data
        2. Writers don't overwrite each other's data
        """
        db = tmp_path / "concurrent.json"

        # Number of operations to perform
        num_iterations = 20

        def writer_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
            """Worker that repeatedly writes data."""
            try:
                storage = TodoStorage(str(db))
                for i in range(num_iterations):
                    todos = [Todo(id=j, text=f"w{worker_id}-iter{i}-item{j}")
                             for j in range(5)]
                    storage.save(todos)
                result_queue.put(("success", worker_id, num_iterations))
            except Exception as e:
                result_queue.put(("error", worker_id, str(e)))

        def reader_worker(reader_id: int, result_queue: multiprocessing.Queue) -> None:
            """Worker that repeatedly reads data and validates it."""
            try:
                storage = TodoStorage(str(db))
                valid_reads = 0
                for _ in range(num_iterations):
                    loaded = storage.load()
                    # Verify data is valid (not corrupted)
                    if len(loaded) > 0:
                        # All items should have valid text
                        for todo in loaded:
                            assert isinstance(todo.text, str), (
                                f"Invalid todo text: {todo.text}"
                            )
                            assert todo.text.startswith("w"), (
                                f"Unexpected text format: {todo.text}"
                            )
                    valid_reads += 1
                    time.sleep(0.001)  # Small delay to increase race likelihood
                result_queue.put(("success", reader_id, valid_reads))
            except (json.JSONDecodeError, ValueError) as e:
                result_queue.put(("corruption", reader_id, str(e)))
            except Exception as e:
                result_queue.put(("error", reader_id, str(e)))

        # Create initial data
        storage = TodoStorage(str(db))
        storage.save([Todo(id=0, text="w0-iter0-item0")])

        # Start workers
        processes = []
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        # 2 writers
        for i in range(2):
            p = multiprocessing.Process(target=writer_worker, args=(i, result_queue))
            processes.append(p)
            p.start()

        # 3 readers
        for i in range(3):
            p = multiprocessing.Process(target=reader_worker, args=(i, result_queue))
            processes.append(p)
            p.start()

        # Wait for all to complete
        for p in processes:
            p.join(timeout=30)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Check for corruption errors - this is the key assertion
        corruptions = [r for r in results if r[0] == "corruption"]
        assert len(corruptions) == 0, (
            f"Data corruption detected! Corruptions: {corruptions}"
        )

        # Check for other errors
        errors = [r for r in results if r[0] == "error"]
        assert len(errors) == 0, f"Workers encountered errors: {errors}"

        # All should succeed
        successes = [r for r in results if r[0] == "success"]
        assert len(successes) == 5, f"Expected 5 successes, got {len(successes)}"

    def test_lock_prevents_reader_seeing_partial_write(self, tmp_path: Path) -> None:
        """Test that a reader blocks until a writer completes.

        This test verifies that when a writer is in the middle of saving,
        a reader will wait and see the complete data, not partial data.
        """
        db = tmp_path / "partial.json"
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text="initial")])

        reader_complete = multiprocessing.Event()
        writer_started = multiprocessing.Event()

        def writer_process():
            """Writer that holds lock while writing."""
            storage = TodoStorage(str(db))
            # Signal that writer is starting
            writer_started.set()
            # Write large data
            todos = [Todo(id=i, text=f"writer-item-{i}" * 100)
                     for i in range(100)]
            storage.save(todos)

        def reader_process(result_queue: multiprocessing.Queue):
            """Reader that reads concurrently."""
            storage = TodoStorage(str(db))
            # Wait for writer to start
            writer_started.wait(timeout=5)
            # Try to read - should block until writer completes
            loaded = storage.load()
            # Verify we got valid data
            result_queue.put(("success", len(loaded)))
            reader_complete.set()

        # Start writer
        p_writer = multiprocessing.Process(target=writer_process)
        p_writer.start()

        # Start reader
        result_queue: multiprocessing.Queue = multiprocessing.Queue()
        p_reader = multiprocessing.Process(
            target=reader_process, args=(result_queue,)
        )
        p_reader.start()

        # Wait for both to complete
        p_writer.join(timeout=30)
        p_reader.join(timeout=30)

        # Reader should have completed
        assert reader_complete.is_set(), "Reader did not complete"

        # Verify reader saw valid data
        while not result_queue.empty():
            result = result_queue.get()
            assert result[0] == "success", f"Reader failed: {result}"
            # Reader should see either initial data or writer's data
            # but never corrupted data
            assert result[1] in (1, 100), f"Unexpected item count: {result[1]}"

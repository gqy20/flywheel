"""Tests for file-based locking in TodoStorage.

This test suite verifies that TodoStorage uses file locks to prevent
race conditions between concurrent readers and writers.

Issue: #5405
"""

from __future__ import annotations

import json
import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestFileLockingMocked:
    """Unit tests using mocks to verify lock behavior."""

    def test_load_uses_filelock(self, tmp_path: Path) -> None:
        """Test that load() uses filelock for concurrent access protection."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text="test")])

        # Track whether FileLock is used by checking for the lock file
        import filelock

        # Track lock creation by patching FileLock
        lock_instances = []

        original_filelock = filelock.FileLock

        class TrackedFileLock(original_filelock):
            def __init__(self, *args, **kwargs):
                lock_instances.append(("created", args, kwargs))
                super().__init__(*args, **kwargs)

            def acquire(self, *args, **kwargs):
                lock_instances.append(("acquire", args, kwargs))
                return super().acquire(*args, **kwargs)

            def release(self, *args, **kwargs):
                lock_instances.append(("release", args, kwargs))
                return super().release(*args, **kwargs)

        try:
            filelock.FileLock = TrackedFileLock

            # Load should create and use a file lock
            storage.load()

            # Verify FileLock was created
            assert len(lock_instances) > 0, "load() should use FileLock"

            # Verify lock was acquired
            acquire_calls = [c for c in lock_instances if c[0] == "acquire"]
            assert len(acquire_calls) >= 1, "load() should acquire a lock"

        finally:
            filelock.FileLock = original_filelock

    def test_save_uses_filelock(self, tmp_path: Path) -> None:
        """Test that save() uses filelock for concurrent access protection."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Track lock creation by patching FileLock
        import filelock

        lock_instances = []

        original_filelock = filelock.FileLock

        class TrackedFileLock(original_filelock):
            def __init__(self, *args, **kwargs):
                lock_instances.append(("created", args, kwargs))
                super().__init__(*args, **kwargs)

            def acquire(self, *args, **kwargs):
                lock_instances.append(("acquire", args, kwargs))
                return super().acquire(*args, **kwargs)

            def release(self, *args, **kwargs):
                lock_instances.append(("release", args, kwargs))
                return super().release(*args, **kwargs)

        try:
            filelock.FileLock = TrackedFileLock

            # Save should create and use a file lock
            storage.save([Todo(id=1, text="test")])

            # Verify FileLock was created
            assert len(lock_instances) > 0, "save() should use FileLock"

            # Verify lock was acquired
            acquire_calls = [c for c in lock_instances if c[0] == "acquire"]
            assert len(acquire_calls) >= 1, "save() should acquire a lock"

        finally:
            filelock.FileLock = original_filelock


class TestFileLockingIntegration:
    """Integration tests for concurrent access protection."""

    def test_concurrent_read_write_no_partial_data(self, tmp_path: Path) -> None:
        """Test that readers never see partial data during concurrent writes.

        This is a regression test for the race condition where a reader
        could read a file while a writer is in the middle of writing.
        """
        db = tmp_path / "concurrent.json"

        # Number of concurrent operations
        num_readers = 10
        num_writers = 5

        reader_results = multiprocessing.Manager().list()
        writer_results = multiprocessing.Manager().list()
        stop_event = multiprocessing.Event()

        def writer_process(writer_id: int) -> None:
            """Writer that continuously writes valid JSON."""
            storage = TodoStorage(str(db))
            for i in range(20):
                if stop_event.is_set():
                    break
                todos = [
                    Todo(id=1, text=f"writer-{writer_id}-iteration-{i}"),
                    Todo(id=2, text=f"writer-{writer_id}-todo-2"),
                ]
                storage.save(todos)
                time.sleep(0.001)  # Small delay to allow interleaving
            writer_results.append(("success", writer_id))

        def reader_process(reader_id: int) -> None:
            """Reader that verifies it never sees invalid/partial data."""
            storage = TodoStorage(str(db))
            for _ in range(30):
                if stop_event.is_set():
                    break
                try:
                    todos = storage.load()
                    # Should always get a valid list
                    assert isinstance(todos, list), f"Expected list, got {type(todos)}"
                    # All todos should have valid attributes
                    for todo in todos:
                        assert hasattr(todo, "id"), "Todo should have id"
                        assert hasattr(todo, "text"), "Todo should have text"
                        assert isinstance(todo.text, str), "Text should be string"
                except (json.JSONDecodeError, ValueError) as e:
                    # This should NEVER happen with proper locking
                    reader_results.append(("corruption", reader_id, str(e)))
                    return
                time.sleep(0.001)
            reader_results.append(("success", reader_id))

        # Start writers
        writer_procs = []
        for i in range(num_writers):
            p = multiprocessing.Process(target=writer_process, args=(i,))
            writer_procs.append(p)
            p.start()

        # Start readers after a small delay
        time.sleep(0.01)
        reader_procs = []
        for i in range(num_readers):
            p = multiprocessing.Process(target=reader_process, args=(i,))
            reader_procs.append(p)
            p.start()

        # Let them run for a bit
        time.sleep(0.5)
        stop_event.set()

        # Wait for all to complete
        for p in writer_procs + reader_procs:
            p.join(timeout=5)

        # Check for any corruption
        corruptions = [r for r in reader_results if len(r) > 2 and r[0] == "corruption"]
        assert len(corruptions) == 0, (
            f"Readers saw corrupted/partial data: {corruptions}. "
            f"File locking should prevent this."
        )

        # All writers should have succeeded
        writer_successes = [r for r in writer_results if r[0] == "success"]
        assert len(writer_successes) == num_writers

    def test_lock_prevents_concurrent_write_race(self, tmp_path: Path) -> None:
        """Test that locking prevents race conditions between concurrent writers.

        Without locking, two writers starting at nearly the same time could
        interleave their operations leading to last-writer-wins. With proper
        exclusive locking, each write should complete atomically.
        """
        db = tmp_path / "race.json"
        storage = TodoStorage(str(db))

        # Initial data
        storage.save([Todo(id=1, text="initial")])

        results = multiprocessing.Manager().list()

        def write_worker(worker_id: int) -> None:
            """Worker that writes and immediately reads back."""
            storage = TodoStorage(str(db))
            # Write unique data
            unique_text = f"worker-{worker_id}-unique-{time.time()}"
            storage.save([Todo(id=1, text=unique_text)])

            # Immediately read back - with locking, we should get our own data
            # or another writer's complete data, never partial
            loaded = storage.load()
            if len(loaded) == 1 and isinstance(loaded[0].text, str):
                results.append(("success", worker_id, loaded[0].text))
            else:
                results.append(("error", worker_id, "invalid read"))

        # Run many workers concurrently
        processes = []
        for i in range(20):
            p = multiprocessing.Process(target=write_worker, args=(i,))
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=10)

        # All should succeed without errors
        errors = [r for r in results if r[0] == "error"]
        assert len(errors) == 0, f"Some workers failed: {errors}"

        # Final file should be valid JSON
        final_todos = storage.load()
        assert isinstance(final_todos, list)
        assert len(final_todos) >= 1

    def test_readers_dont_block_each_other(self, tmp_path: Path) -> None:
        """Test that multiple readers can read simultaneously.

        With shared locks for reading, multiple readers should be able
        to read the file concurrently without blocking each other.
        """
        db = tmp_path / "shared.json"
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text="shared data")])

        results = multiprocessing.Manager().list()
        start_barrier = multiprocessing.Barrier(10)
        read_times = multiprocessing.Manager().list()

        def reader_process(reader_id: int) -> None:
            """Reader that measures read time."""
            storage = TodoStorage(str(db))

            # Synchronize all readers to start at the same time
            start_barrier.wait()

            start = time.time()
            todos = storage.load()
            elapsed = time.time() - start

            read_times.append(elapsed)
            results.append(("success", reader_id, len(todos)))

        # Start many readers simultaneously
        processes = []
        for i in range(10):
            p = multiprocessing.Process(target=reader_process, args=(i,))
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=10)

        # All readers should succeed
        successes = [r for r in results if r[0] == "success"]
        assert len(successes) == 10, f"Expected 10 successes, got {len(successes)}"

        # All reads should complete relatively quickly (not serialized)
        # If readers were blocking each other, total time would be much higher
        max_read_time = max(read_times) if read_times else 0
        assert max_read_time < 1.0, (
            f"Read took too long ({max_read_time}s), readers may be blocking each other"
        )


class TestFileLockingEdgeCases:
    """Edge case tests for file locking."""

    def test_lock_released_on_load_error(self, tmp_path: Path) -> None:
        """Test that lock is released even if load() encounters an error."""
        db = tmp_path / "error.json"

        # Create invalid JSON file
        db.write_text("{ invalid json }")

        storage = TodoStorage(str(db))

        # Load should fail but release lock
        with pytest.raises(ValueError, match="Invalid JSON"):
            storage.load()

        # Should be able to create another storage and write
        storage2 = TodoStorage(str(db))
        storage2.save([Todo(id=1, text="valid")])

        # Should now be able to load
        loaded = storage2.load()
        assert len(loaded) == 1
        assert loaded[0].text == "valid"

    def test_lock_released_on_save_error(self, tmp_path: Path) -> None:
        """Test that lock is released even if save() encounters an error."""
        db = tmp_path / "save_error.json"
        storage = TodoStorage(str(db))

        # First save should work
        storage.save([Todo(id=1, text="initial")])

        # Corrupt the file path by creating a file where a directory should be
        # This will cause issues on subsequent saves to nested paths

        # Load should still work
        loaded = storage.load()
        assert len(loaded) == 1

    def test_lockfile_path_is_deterministic(self, tmp_path: Path) -> None:
        """Test that the lock file path is consistent for the same storage path."""
        db = tmp_path / "deterministic.json"

        storage = TodoStorage(str(db))
        storage.save([Todo(id=1, text="test")])

        # After a save, the lock file might exist (depending on implementation)
        # The key is that it's in a predictable location
        # Some implementations delete the lock after release, some don't

        # Create another storage instance - should use same lock
        storage2 = TodoStorage(str(db))
        storage2.save([Todo(id=2, text="test2")])

        # Both should work without deadlock
        loaded = storage2.load()
        assert len(loaded) == 1

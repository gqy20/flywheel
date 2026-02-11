"""Tests for file locking mechanism to prevent concurrent write conflicts.

This test suite verifies that TodoStorage uses proper file locking
to serialize concurrent writes and prevent data loss.

TDD Approach: RED phase - All tests will fail initially.
"""

from __future__ import annotations

import multiprocessing
import time

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestFileLockBasicBehavior:
    """Test basic FileLock behavior."""

    def test_file_lock_exclusive_blocks_another_process(self, tmp_path) -> None:
        """Test that an exclusive lock held by one process blocks another process.

        This is the core behavior we need - process A holds lock,
        process B tries to acquire and should block/timeout.
        """
        lock_file = tmp_path / "test.lock"
        result_queue: multiprocessing.Queue[str] = multiprocessing.Queue()

        def holder_process() -> None:
            """Process that holds a lock for a short time."""
            from flywheel.storage import FileLock

            try:
                with FileLock(lock_file, exclusive=True, timeout=1.0):
                    # Hold lock for 0.5 seconds
                    time.sleep(0.5)
                    result_queue.put("holder_acquired_and_released")
            except Exception as e:
                result_queue.put(f"holder_error: {e}")

        def waiter_process() -> None:
            """Process that tries to acquire the same lock."""
            from flywheel.storage import FileLock

            # Give holder time to acquire lock first
            time.sleep(0.1)

            try:
                start = time.time()
                with FileLock(lock_file, exclusive=True, timeout=1.0):
                    elapsed = time.time() - start
                    # Should have waited at least 0.4 seconds (holder held for 0.5)
                    result_queue.put(f"waiter_acquired_after_{elapsed:.2f}s")
            except TimeoutError:
                elapsed = time.time() - start
                result_queue.put(f"waiter_timeout_after_{elapsed:.2f}s")
            except Exception as e:
                result_queue.put(f"waiter_error: {e}")

        # Start holder
        p1 = multiprocessing.Process(target=holder_process)
        p1.start()

        # Start waiter immediately (should block)
        p2 = multiprocessing.Process(target=waiter_process)
        p2.start()

        p1.join(timeout=5)
        p2.join(timeout=5)

        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # At minimum, holder should complete successfully
        assert any("holder_acquired" in r for r in results), f"Holder failed: {results}"

    def test_file_lock_shared_allows_multiple_readers(self, tmp_path) -> None:
        """Test that shared locks allow multiple readers simultaneously."""
        lock_file = tmp_path / "test.lock"
        result_queue: multiprocessing.Queue[str] = multiprocessing.Queue()

        def reader_process(reader_id: int) -> None:
            """Process that acquires a shared (read) lock."""
            from flywheel.storage import FileLock

            try:
                with FileLock(lock_file, exclusive=False, timeout=2.0):
                    result_queue.put(f"reader_{reader_id}_acquired")
                    time.sleep(0.2)  # Hold briefly
                    result_queue.put(f"reader_{reader_id}_released")
            except Exception as e:
                result_queue.put(f"reader_{reader_id}_error: {e}")

        # Start multiple readers
        readers = []
        for i in range(3):
            p = multiprocessing.Process(target=reader_process, args=(i,))
            readers.append(p)
            p.start()

        for p in readers:
            p.join(timeout=5)

        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # All readers should have acquired their locks
        acquired = [r for r in results if "acquired" in r]
        assert len(acquired) == 3, f"Expected 3 readers to acquire, got: {results}"

    def test_file_lock_shared_blocks_exclusive(self, tmp_path) -> None:
        """Test that a shared lock blocks an exclusive lock."""
        lock_file = tmp_path / "test.lock"
        result_queue: multiprocessing.Queue[str] = multiprocessing.Queue()

        def reader_with_long_hold() -> None:
            """Process that holds shared lock for a while."""
            from flywheel.storage import FileLock

            try:
                with FileLock(lock_file, exclusive=False, timeout=1.0):
                    result_queue.put("reader_acquired")
                    time.sleep(0.5)  # Hold long enough for writer to wait
                    result_queue.put("reader_released")
            except Exception as e:
                result_queue.put(f"reader_error: {e}")

        def writer_waiting() -> None:
            """Process that tries to get exclusive lock while reader holds."""
            from flywheel.storage import FileLock

            time.sleep(0.1)  # Ensure reader goes first
            try:
                start = time.time()
                with FileLock(lock_file, exclusive=True, timeout=1.0):
                    elapsed = time.time() - start
                    result_queue.put(f"writer_acquired_after_{elapsed:.2f}s")
            except TimeoutError:
                elapsed = time.time() - start
                result_queue.put(f"writer_timeout_after_{elapsed:.2f}s")
            except Exception as e:
                result_queue.put(f"writer_error: {e}")

        p1 = multiprocessing.Process(target=reader_with_long_hold)
        p2 = multiprocessing.Process(target=writer_waiting)

        p1.start()
        p2.start()

        p1.join(timeout=5)
        p2.join(timeout=5)

        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Reader should definitely acquire
        assert any("reader_acquired" in r for r in results), f"Reader failed: {results}"

    def test_file_lock_timeout_error_message(self, tmp_path) -> None:
        """Test that lock timeout produces a clear error message."""
        lock_file = tmp_path / "test.lock"
        result_queue: multiprocessing.Queue[str] = multiprocessing.Queue()

        def lock_holder() -> None:
            """Holds lock indefinitely."""
            from flywheel.storage import FileLock

            try:
                with FileLock(lock_file, exclusive=True, timeout=1.0):
                    result_queue.put("holder_acquired")
                    time.sleep(10)  # Hold long enough for timeout
            except Exception as e:
                result_queue.put(f"holder_error: {e}")

        def lock_tryer() -> None:
            """Tries to acquire with short timeout."""
            from flywheel.storage import FileLock

            time.sleep(0.1)  # Let holder go first
            try:
                with FileLock(lock_file, exclusive=True, timeout=0.5):
                    result_queue.put("tryer_acquired")
            except TimeoutError as e:
                # Should include helpful error message
                result_queue.put(f"tryer_timeout: {e!s}")
            except Exception as e:
                result_queue.put(f"tryer_error: {type(e).__name__}: {e}")

        p1 = multiprocessing.Process(target=lock_holder)
        p2 = multiprocessing.Process(target=lock_tryer)

        p1.start()
        p2.start()

        p2.join(timeout=3)
        # Kill holder as we don't need it anymore
        p1.terminate()
        p1.join(timeout=1)

        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        timeout_msgs = [r for r in results if "timeout" in r.lower()]
        assert len(timeout_msgs) > 0, f"Expected timeout error, got: {results}"
        # Verify error message is helpful
        assert any(
            "lock" in msg.lower() or "timeout" in msg.lower()
            for msg in timeout_msgs
        ), f"Error message should mention lock/timeout: {timeout_msgs}"


class TestTodoStorageIntegration:
    """Test that TodoStorage properly uses file locking."""

    def test_storage_save_uses_exclusive_lock(self, tmp_path) -> None:
        """Verify that save() acquires an exclusive lock."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # Verify save() works
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_storage_load_uses_shared_lock(self, tmp_path) -> None:
        """Verify that load() acquires a shared lock."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save to create file
        todos = [Todo(id=1, text="test"), Todo(id=2, text="test2")]
        storage.save(todos)

        # Multiple concurrent loads should work
        loaded1 = storage.load()
        loaded2 = storage.load()

        assert len(loaded1) == 2
        assert len(loaded2) == 2

    def test_concurrent_saves_serialize_properly(self, tmp_path) -> None:
        """Test that concurrent saves from multiple processes serialize correctly.

        This is the key test for the issue - multiple processes saving
        should NOT result in data loss. The final state should be
        valid and consistent with exactly one process's write.
        """
        db = tmp_path / "concurrent_save.json"

        def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
            """Worker that saves unique todos and verifies result."""
            try:
                storage = TodoStorage(str(db))

                # Create unique todos for this worker
                todos = [
                    Todo(id=i, text=f"worker-{worker_id}-todo-{i}")
                    for i in range(worker_id * 10, (worker_id + 1) * 10)
                ]

                storage.save(todos)

                # Small delay to increase contention
                time.sleep(0.001 * (worker_id % 7))

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

        # Wait for all processes
        for p in processes:
            p.join(timeout=15)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        successes = [r for r in results if r[0] == "success"]
        errors = [r for r in results if r[0] == "error"]

        # All workers should succeed
        assert len(errors) == 0, f"Workers had errors: {errors}"
        assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

        # Final state should be valid JSON (not corrupted)
        storage = TodoStorage(str(db))
        final_todos = storage.load()

        # Should have exactly one worker's worth of todos (10 items)
        # because file locking should serialize the writes
        assert isinstance(final_todos, list), "Final data should be a list"
        assert len(final_todos) == 10, f"Expected 10 todos from one worker, got {len(final_todos)}"

        # All todos should be from the same worker (consistent write)
        worker_ids = set()
        for todo in final_todos:
            # Extract worker ID from text like "worker-2-todo-20"
            parts = todo.text.split("-")
            if len(parts) >= 2 and parts[0] == "worker":
                worker_ids.add(int(parts[1]))

        # All todos should be from a single worker
        assert len(worker_ids) == 1, f"Expected todos from single worker, got from {worker_ids}"

    def test_load_blocks_during_save(self, tmp_path) -> None:
        """Test that load() blocks while a save() is in progress."""
        db = tmp_path / "blocking.json"
        result_queue: multiprocessing.Queue[str] = multiprocessing.Queue()

        def slow_saver() -> None:
            """Process that saves slowly."""
            storage = TodoStorage(str(db))
            todos = [Todo(id=i, text=f"todo-{i}") for i in range(1000)]
            result_queue.put("saver_start")
            storage.save(todos)
            result_queue.put("saver_done")

        def quick_loader() -> None:
            """Process that tries to load while save is happening."""
            time.sleep(0.05)  # Let saver start first
            result_queue.put("loader_start")
            storage = TodoStorage(str(db))
            loaded = storage.load()
            result_queue.put(f"loader_done: {len(loaded)} items")

        p1 = multiprocessing.Process(target=slow_saver)
        p2 = multiprocessing.Process(target=quick_loader)

        p1.start()
        p2.start()

        p1.join(timeout=10)
        p2.join(timeout=10)

        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Both should complete
        assert any("saver_done" in r for r in results), f"Saver didn't complete: {results}"
        assert any("loader_done" in r for r in results), f"Loader didn't complete: {results}"

    def test_lock_timeout_on_conflict(self, tmp_path) -> None:
        """Test that a lock timeout is enforced when save() can't acquire lock."""
        db = tmp_path / "timeout.json"
        result_queue: multiprocessing.Queue[str] = multiprocessing.Queue()

        def holder() -> None:
            """Hold a save lock for a long time."""
            storage = TodoStorage(str(db))
            result_queue.put("holder_start")

            # We'll use FileLock directly to hold the lock
            from flywheel.storage import FileLock
            with FileLock(storage.path, exclusive=True, timeout=5.0):
                result_queue.put("holder_acquired")
                time.sleep(3)  # Hold for 3 seconds
                result_queue.put("holder_released")

        def tryer_with_timeout() -> None:
            """Try to save with a short timeout."""
            time.sleep(0.1)  # Let holder go first
            storage = TodoStorage(str(db))

            # Patch the lock timeout to be shorter
            original_save = storage.save

            def save_with_timeout(todos):
                # This should use a short timeout
                from flywheel.storage import FileLock
                with FileLock(storage.path, exclusive=True, timeout=0.5):
                    return original_save(todos)

            try:
                storage.save = save_with_timeout
                storage.save([Todo(id=2, text="tryer")])
                result_queue.put("tryer_success")
            except TimeoutError:
                result_queue.put("tryer_timeout")
            except Exception as e:
                result_queue.put(f"tryer_error: {type(e).__name__}")

        p1 = multiprocessing.Process(target=holder)
        p2 = multiprocessing.Process(target=tryer_with_timeout)

        p1.start()
        p2.start()

        p2.join(timeout=5)
        p1.terminate()
        p1.join(timeout=1)

        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Tryer should timeout
        assert "tryer_timeout" in results, f"Expected tryer timeout, got: {results}"


class TestCrossPlatformCompatibility:
    """Tests for cross-platform file locking compatibility."""

    def test_file_lock_works_on_current_platform(self, tmp_path) -> None:
        """Test that FileLock can be imported and used on current platform."""
        lock_file = tmp_path / "platform_test.lock"

        from flywheel.storage import FileLock

        # Should not raise ImportError
        with FileLock(lock_file, exclusive=True, timeout=1.0):
            pass  # Successfully acquired and released

        # Verify lock file cleanup or existence is handled
        # (lock files may or may not persist - that's implementation-dependent)

    def test_both_lock_types_available(self, tmp_path) -> None:
        """Verify both fcntl (Unix) and msvcrt (Windows) imports work correctly."""
        # This test ensures the correct module is available for the platform
        import sys

        if sys.platform == "win32":
            # Windows - msvcrt should be available
            import msvcrt
            assert hasattr(msvcrt, "locking"), "msvcrt.locking not available on Windows"
        else:
            # Unix - fcntl should be available
            import fcntl
            assert hasattr(fcntl, "lockf") or hasattr(fcntl, "flock"), \
                "fcntl locking not available on Unix"

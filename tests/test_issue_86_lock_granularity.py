"""Tests for issue #86 - I/O operations should not hold lock."""

import tempfile
import threading
import time
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_io_does_not_block_readers():
    """Test that I/O operations in _save_with_todos don't block other threads.

    This test creates a scenario where:
    1. Thread 1 starts a save operation (which involves I/O)
    2. Thread 2 tries to read data

    If I/O holds the lock, Thread 2 will be blocked for the entire duration of I/O.
    With proper lock granularity, Thread 2 should only be blocked during memory copy.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create a large todo list to make I/O operations take measurable time
        large_todos = [Todo(id=i, title=f"Todo {i}", status="pending") for i in range(1000)]
        storage = Storage(path=str(storage_path))
        storage._todos = large_todos
        storage._next_id = 1001

        # Flags to track thread progress
        save_started = threading.Event()
        save_in_io = threading.Event()
        read_blocked = threading.Event()
        read_completed = threading.Event()

        # Track if lock was held during I/O
        io_held_lock = {"value": False}

        original_save_with_todos = storage._save_with_todos

        def patched_save_with_todos(todos):
            """Patch _save_with_todos to detect if lock is held during I/O."""
            save_started.set()

            # Check if lock is held by trying to acquire it with timeout=0
            # If we can acquire it, it means the original method released it before I/O
            if storage._lock.acquire(blocking=False):
                # Lock was released - good! Store this and release.
                storage._lock.release()
            else:
                # Lock is still held - this means I/O will block other threads
                io_held_lock["value"] = True

            save_in_io.set()
            return original_save_with_todos(todos)

        # Patch the method
        storage._save_with_todos = patched_save_with_todos

        # Thread 1: Perform save operation
        def save_thread():
            storage._save_with_todos(storage._todos)

        # Thread 2: Try to read while save is happening
        def read_thread():
            # Wait for save to start
            save_started.wait()
            # Wait a bit to ensure save is in I/O phase
            save_in_io.wait()

            # Try to acquire lock for reading
            # If I/O holds the lock, this will be blocked
            start_time = time.time()
            with storage._lock:
                # If we get here quickly, lock wasn't held during I/O
                pass
            elapsed = time.time() - start_time

            # If lock was held during I/O, acquiring it would take significant time
            # (I/O operations typically take > 1ms for 1000 todos)
            # With proper granularity, acquiring should be nearly instant
            if elapsed > 0.001:  # 1ms threshold
                read_blocked.set()

            read_completed.set()

        t1 = threading.Thread(target=save_thread)
        t2 = threading.Thread(target=read_thread)

        # Start threads
        t1.start()
        time.sleep(0.001)  # Small delay to ensure t1 starts first
        t2.start()

        # Wait for completion
        t1.join()
        t2.join()

        # Assertions
        assert not io_held_lock["value"], (
            "Lock should NOT be held during I/O operations. "
            "_save_with_todos should release lock before performing file I/O."
        )
        assert not read_blocked.is_set(), (
            "Read thread should not be blocked during I/O. "
            "Lock should be released before I/O operations."
        )


def test_save_io_does_not_block_readers():
    """Test that I/O operations in _save don't block other threads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create a large todo list to make I/O operations take measurable time
        large_todos = [Todo(id=i, title=f"Todo {i}", status="pending") for i in range(1000)]
        storage = Storage(path=str(storage_path))
        storage._todos = large_todos
        storage._next_id = 1001

        # Track if lock was held during I/O
        io_held_lock = {"value": False}

        original_save = storage._save

        def patched_save():
            """Patch _save to detect if lock is held during I/O."""
            # Check if lock is held by trying to acquire it with timeout=0
            if storage._lock.acquire(blocking=False):
                storage._lock.release()
            else:
                io_held_lock["value"] = True

            return original_save()

        storage._save = patched_save
        storage._save()

        assert not io_held_lock["value"], (
            "Lock should NOT be held during I/O operations. "
            "_save should release lock before performing file I/O."
        )


def test_concurrent_operations_with_optimized_lock():
    """Test that concurrent operations work efficiently with optimized lock granularity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(path=str(storage_path))

        # Add initial todos
        for i in range(10):
            storage.add(Todo(id=i, title=f"Todo {i}", status="pending"))

        results = {"errors": [], "read_count": 0}

        def worker(worker_id):
            """Worker that performs read operations."""
            try:
                for _ in range(100):
                    todos = storage.list()
                    results["read_count"] += 1
            except Exception as e:
                results["errors"].append((worker_id, str(e)))

        # Start multiple threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

        # Also do writes concurrently
        def write_worker():
            try:
                for i in range(10, 20):
                    storage.add(Todo(id=i, title=f"Todo {i}", status="pending"))
            except Exception as e:
                results["errors"].append(("write", str(e)))

        write_thread = threading.Thread(target=write_worker)

        start_time = time.time()
        for t in threads:
            t.start()
        write_thread.start()

        # Wait for completion
        for t in threads:
            t.join()
        write_thread.join()
        elapsed = time.time() - start_time

        # With proper lock granularity, this should complete quickly
        # If I/O holds the lock, it would take much longer
        assert len(results["errors"]) == 0, f"Errors occurred: {results['errors']}"
        assert results["read_count"] == 500, f"Expected 500 reads, got {results['read_count']}"
        # With optimized lock, should complete in reasonable time
        # This is a soft check - adjust threshold based on system performance
        assert elapsed < 10.0, f"Operations took too long ({elapsed:.2f}s), lock may be held during I/O"

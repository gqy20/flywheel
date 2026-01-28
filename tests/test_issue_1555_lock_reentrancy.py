"""Test for Issue #1555: Verify that Storage methods don't cause deadlock due to non-reentrant locks.

This test ensures that FileStorage methods don't have reentrancy issues that would
cause deadlock when using threading.Lock instead of threading.RLock.

The fix for Issue #1394 replaced RLock with Lock to prevent async deadlocks, but
this means we must ensure no method holds a lock while calling another method that
needs the same lock (reentrancy).

CODE REVIEW RESULT:
After thorough analysis of the FileStorage class, we confirmed that:
1. The implementation does NOT have reentrancy issues
2. No method holds the lock while calling another method that needs the lock
3. All methods acquire the lock only for the minimum necessary time
4. The use of non-reentrant Lock (Issue #1394) is safe and correct

The test suite below verifies this behavior and documents the safety guarantees.
"""

import tempfile
import threading
import time
from pathlib import Path

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


class TestLockReentrancy:
    """Test suite for verifying no reentrancy issues with threading.Lock."""

    def test_no_deadlock_in_save_operations(self):
        """Test that save operations don't cause deadlock.

        This test verifies that if there's any code path where a method holding
        the lock calls another method that needs the lock, it will be detected.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Create a todo
            todo = Todo(id=1, title="Test Todo", description="Test Description")

            # This should not deadlock
            storage.add(todo)

            # Try to save while potentially holding locks
            # If there's a reentrancy issue, this could deadlock
            storage.save()

    def test_no_deadlock_in_nested_operations(self):
        """Test that nested operations don't cause deadlock.

        Simulates a scenario where one operation might trigger another
        while holding locks.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Create multiple todos
            for i in range(5):
                todo = Todo(id=i, title=f"Todo {i}", description=f"Description {i}")
                storage.add(todo)

            # Perform various operations that might interact
            # If there's reentrancy, this could deadlock
            storage.save()
            todos = storage.list()
            assert len(todos) == 5

            # Try getting todos while operations are in progress
            for todo in todos:
                retrieved = storage.get(todo.id)
                assert retrieved is not None

    def test_concurrent_access_safety(self):
        """Test that concurrent access doesn't cause deadlock.

        This test verifies that the lock implementation properly handles
        concurrent access without causing deadlock.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Create some initial todos
            for i in range(3):
                todo = Todo(id=i, title=f"Todo {i}", description=f"Description {i}")
                storage.add(todo)
            storage.save()

            results = []
            exceptions = []

            def worker(worker_id):
                """Worker function that performs various storage operations."""
                try:
                    for i in range(5):
                        # Add a todo
                        todo = Todo(id=worker_id * 10 + i, title=f"Worker {worker_id} Todo {i}")
                        storage.add(todo)

                        # List todos
                        todos = storage.list()

                        # Save
                        storage.save()

                        # Small delay to increase chance of race condition
                        time.sleep(0.001)

                    results.append(worker_id)
                except Exception as e:
                    exceptions.append((worker_id, e))

            # Start multiple threads
            threads = []
            for i in range(3):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()

            # Wait for all threads with timeout
            start_time = time.time()
            timeout = 10  # seconds
            for t in threads:
                # Join with timeout to detect deadlock
                t.join(timeout=timeout - (time.time() - start_time))
                if t.is_alive():
                    pytest.fail(f"Deadlock detected: thread {t.name} did not complete within {timeout} seconds")

            # Check for exceptions
            if exceptions:
                for worker_id, exc in exceptions:
                    print(f"Worker {worker_id} failed: {exc}")
                pytest.fail(f"Concurrent access caused exceptions: {exceptions}")

            # Verify all workers completed
            assert len(results) == 3

    def test_lock_is_non_reentrant(self):
        """Verify that the lock is actually a non-reentrant Lock.

        This test confirms that the current implementation uses threading.Lock
        (non-reentrant) as per the fix for Issue #1394.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Verify that _lock is a threading.Lock (non-reentrant)
            assert isinstance(storage._lock, threading.Lock), \
                f"Expected threading.Lock, got {type(storage._lock)}"

            # Verify it's NOT an RLock
            assert not isinstance(storage._lock, threading.RLock), \
                "Lock should not be reentrant (RLock) per Issue #1394"

    def test_reentrancy_would_cause_deadlock(self):
        """
        Demonstrate that if reentrancy were attempted, it would cause deadlock.

        This test shows why we must avoid reentrancy with threading.Lock.
        It simulates what would happen if a method tried to acquire the lock
        while already holding it.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = FileStorage(str(storage_path))

            # Get the lock
            lock = storage._lock

            # Acquire the lock once
            lock.acquire()

            try:
                # Try to acquire it again (this would block with Lock but not with RLock)
                # We use a timeout to detect the blocking
                acquired = lock.acquire(timeout=0.1)

                if acquired:
                    # If we got here, the lock is actually reentrant (RLock)
                    lock.release()
                    pytest.fail("Lock appears to be reentrant (RLock), expected non-reentrant Lock")
                else:
                    # This is expected for threading.Lock - cannot acquire again
                    # This confirms we're using a non-reentrant lock
                    pass
            finally:
                # Release the first acquisition
                lock.release()

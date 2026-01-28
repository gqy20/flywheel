"""Test for Issue #1421: Sync lock timeout handling and state consistency.

NOTE: After analysis, the issue #1421 describes a hypothetical concern that is
NOT an actual bug. The current implementation is correct because:
- threading.Lock.acquire(timeout=X) returning False means the lock was NOT acquired
- There is no "state residue" or cleanup needed when acquire() fails
- The current code properly handles the timeout case

These tests VERIFY that the current implementation correctly handles lock timeouts
and maintains state consistency, confirming that no bug exists.

This test verifies that:
1. When lock acquisition times out, a TimeoutError is raised
2. The lock state remains consistent after a timeout
3. No deadlock occurs when timeout happens
4. The lock can be successfully acquired after a timeout
"""
import threading
import time
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed

from flywheel.storage import Flywheel


class TestLockTimeoutHandling:
    """Test suite for issue #1421 - lock timeout and state consistency."""

    def test_lock_timeout_raises_timeout_error(self):
        """Test that lock acquisition timeout raises TimeoutError."""
        fw = Flywheel()

        # Hold the lock in a separate thread to cause timeout
        lock_held = threading.Event()
        release_lock = threading.Event()

        def hold_lock():
            with fw._sync_lock:
                lock_held.set()
                release_lock.wait(timeout=10)

        # Start thread that holds the lock
        holder = threading.Thread(target=hold_lock)
        holder.start()
        lock_held.wait(timeout=5)

        # Try to acquire the lock with a short timeout
        # This should timeout because the lock is held by another thread
        fw._lock_timeout = 0.1  # Set very short timeout

        with pytest.raises(TimeoutError) as exc_info:
            with fw._sync_lock:
                pass

        assert "Could not acquire lock" in str(exc_info.value)
        assert "seconds" in str(exc_info.value)

        # Release the lock holder
        release_lock.set()
        holder.join(timeout=5)

    def test_lock_state_consistency_after_timeout(self, tmp_path):
        """Test that lock state remains consistent after timeout."""
        fw = Flywheel(storage_path=tmp_path)

        # Store initial data
        fw["key1"] = "value1"
        assert fw["key1"] == "value1"

        # Hold the lock in a separate thread
        lock_held = threading.Event()
        release_lock = threading.Event()

        def hold_lock():
            with fw._sync_lock:
                lock_held.set()
                release_lock.wait(timeout=10)

        holder = threading.Thread(target=hold_lock)
        holder.start()
        lock_held.wait(timeout=5)

        # Try to acquire with short timeout - should fail
        fw._lock_timeout = 0.1
        with pytest.raises(TimeoutError):
            with fw._sync_lock:
                pass

        # Release the holder
        release_lock.set()
        holder.join(timeout=5)

        # Now we should be able to acquire the lock normally
        # and the data should be consistent
        with fw._sync_lock:
            assert fw["key1"] == "value1"
            fw["key2"] = "value2"

        # Verify data integrity
        assert fw["key1"] == "value1"
        assert fw["key2"] == "value2"

    def test_multiple_concurrent_lock_attempts(self, tmp_path):
        """Test multiple threads attempting to acquire lock simultaneously."""
        fw = Flywheel(storage_path=tmp_path)
        results = []
        errors = []
        lock_held = threading.Event()
        release_lock = threading.Event()

        def hold_lock_for_duration():
            """Hold the lock to force timeouts in other threads."""
            with fw._sync_lock:
                lock_held.set()
                release_lock.wait(timeout=10)

        def try_acquire_lock(thread_id):
            """Try to acquire the lock."""
            try:
                with fw._sync_lock:
                    results.append(f"Thread {thread_id} acquired lock")
                    fw[f"key_{thread_id}"] = f"value_{thread_id}"
            except TimeoutError as e:
                errors.append(f"Thread {thread_id} timed out: {e}")

        # Start lock holder
        holder = threading.Thread(target=hold_lock_for_duration)
        holder.start()
        lock_held.wait(timeout=5)

        # Set short timeout
        fw._lock_timeout = 0.1

        # Multiple threads try to acquire
        threads = []
        for i in range(5):
            t = threading.Thread(target=try_acquire_lock, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads to finish
        for t in threads:
            t.join(timeout=10)

        # Release the lock holder
        release_lock.set()
        holder.join(timeout=5)

        # Verify some threads timed out (lock was held)
        assert len(errors) > 0, "Expected some threads to timeout"

        # Verify lock is still functional
        with fw._sync_lock:
            fw["final_check"] = "success"

        assert fw["final_check"] == "success"

    def test_lock_functional_after_timeout_exception(self, tmp_path):
        """Test that lock continues to work normally after a TimeoutError."""
        fw = Flywheel(storage_path=tmp_path)

        # Hold lock in thread
        lock_held = threading.Event()
        release_lock = threading.Event()

        def hold_lock():
            with fw._sync_lock:
                lock_held.set()
                release_lock.wait(timeout=10)

        holder = threading.Thread(target=hold_lock)
        holder.start()
        lock_held.wait(timeout=5)

        # Cause timeout
        fw._lock_timeout = 0.1
        timeout_raised = False
        try:
            with fw._sync_lock:
                pass
        except TimeoutError:
            timeout_raised = True

        assert timeout_raised, "TimeoutError should have been raised"

        # Release holder
        release_lock.set()
        holder.join(timeout=5)

        # Now verify lock works normally
        with fw._sync_lock:
            fw["test_key"] = "test_value"

        assert fw["test_key"] == "test_value"

        # Try multiple normal operations
        for i in range(3):
            with fw._sync_lock:
                fw[f"normal_{i}"] = f"value_{i}"

        assert fw["normal_0"] == "value_0"
        assert fw["normal_1"] == "value_1"
        assert fw["normal_2"] == "value_2"

    def test_no_deadlock_from_timeout(self, tmp_path):
        """Test that timeout doesn't cause deadlock."""
        fw = Flywheel(storage_path=tmp_path)
        fw._lock_timeout = 0.5  # Short timeout

        completed_operations = []
        deadlock_detected = threading.Event()

        def worker(worker_id):
            """Worker that tries to acquire lock multiple times."""
            for attempt in range(3):
                try:
                    with fw._sync_lock:
                        completed_operations.append(f"Worker {worker_id} attempt {attempt}")
                        time.sleep(0.05)  # Simulate some work
                except TimeoutError:
                    # Timeout is acceptable, just retry
                    pass

        # Start multiple workers
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(i,))
            t.start()
            threads.append(t)

        # All threads should complete without deadlock
        for t in threads:
            t.join(timeout=15)
            assert not t.is_alive(), f"Thread {t.name} may be deadlocked"

        # Verify some operations completed
        assert len(completed_operations) > 0, "No operations completed - possible deadlock"

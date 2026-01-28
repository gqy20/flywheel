"""Test for Issue #1145: Thread safety of _get_async_lock initialization.

This test verifies that the _get_async_lock method is thread-safe and prevents
multiple Lock objects from being created in concurrent scenarios.
"""
import asyncio
import threading
from flywheel.storage import IOMetrics


def test_get_async_lock_thread_safety():
    """Test that _get_async_lock creates only one lock object even under concurrent access.

    This test simulates multiple threads calling _get_async_lock simultaneously
    to ensure that only one asyncio.Lock is created, preventing race conditions.
    """
    metrics = IOMetrics()

    # Track unique lock objects created
    lock_objects = []
    exceptions = []

    def create_lock_in_thread():
        """Function to be called in multiple threads."""
        try:
            # Each thread tries to get the async lock
            # In the buggy version, this could create multiple Lock objects
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                lock = metrics._get_async_lock()
                lock_objects.append(id(lock))
            finally:
                loop.close()
        except Exception as e:
            exceptions.append(e)

    # Create multiple threads that will all call _get_async_lock concurrently
    threads = []
    num_threads = 10

    for _ in range(num_threads):
        thread = threading.Thread(target=create_lock_in_thread)
        threads.append(thread)

    # Start all threads simultaneously
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check that no exceptions occurred
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

    # The critical assertion: all threads should get the same lock object
    # If there's a race condition, we'll see multiple unique lock IDs
    unique_locks = len(set(lock_objects))
    assert unique_locks == 1, (
        f"Expected 1 unique lock object, but found {unique_locks} unique locks. "
        f"This indicates a race condition in _get_async_lock initialization."
    )

    # Verify that the lock is properly initialized
    assert metrics._lock is not None, "Lock should be initialized"
    assert isinstance(metrics._lock, asyncio.Lock), "Lock should be an asyncio.Lock"


def test_get_async_lock_returns_same_instance():
    """Test that multiple calls to _get_async_lock return the same lock instance."""
    metrics = IOMetrics()

    # Create multiple event loops to simulate different async contexts
    locks = []

    for _ in range(5):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            lock = metrics._get_async_lock()
            locks.append(lock)
        finally:
            loop.close()

    # All locks should be the same object
    first_lock_id = id(locks[0])
    for lock in locks[1:]:
        assert id(lock) == first_lock_id, "All calls should return the same lock instance"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

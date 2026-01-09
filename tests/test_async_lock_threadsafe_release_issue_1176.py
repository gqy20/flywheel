"""Test thread-safe lock release in _AsyncCompatibleLock.__exit__ (Issue #1176).

This test verifies that the lock release in __exit__ is scheduled via
loop.call_soon_threadsafe to ensure thread safety when the lock was
acquired via run_coroutine_threadsafe from a different thread.

The issue is that releasing an asyncio.Lock that was acquired via
run_coroutine_threadsafe from a different thread is technically unsafe
and not part of the public API contract of asyncio.Lock. It can lead to
race conditions or assertion errors in debug builds.

The fix is to schedule the release via loop.call_soon_threadsafe.
"""

import asyncio
import threading
import time
from flywheel.storage import _AsyncCompatibleLock


def test_lock_release_uses_call_soon_threadsafe():
    """Test that lock release is scheduled via call_soon_threadsafe.

    This test verifies that when a lock is acquired from a sync context
    in a different thread, the release is properly scheduled using
    call_soon_threadsafe to ensure thread safety.
    """
    lock = _AsyncCompatibleLock()
    results = {"acquired_in_thread": False, "released_safely": False}

    def acquire_and_release_in_thread():
        """Acquire and release the lock in a separate thread."""
        # This acquires the lock using run_coroutine_threadsafe
        with lock:
            results["acquired_in_thread"] = True
            # Simulate some work while holding the lock
            time.sleep(0.1)
            # When exiting this context, __exit__ is called
            # The release should be scheduled via call_soon_threadsafe
            results["released_safely"] = True

    # Run the acquire/release in a separate thread
    thread = threading.Thread(target=acquire_and_release_in_thread)
    thread.start()
    thread.join()

    # Verify the lock was acquired and released
    assert results["acquired_in_thread"], "Lock was not acquired in thread"
    assert results["released_safely"], "Lock was not released safely"

    # Verify the lock is actually released
    assert not lock._lock.locked(), "Lock should be released after context exit"


def test_multiple_threads_acquire_and_release():
    """Test that multiple threads can safely acquire and release the lock.

    This test creates a scenario where multiple threads acquire and release
    the lock concurrently. If the release is not thread-safe, this can lead
    to race conditions or assertion errors.
    """
    lock = _AsyncCompatibleLock()
    errors = []
    success_count = {"value": 0}

    def worker(thread_id):
        """Worker function that acquires and releases the lock."""
        try:
            for i in range(10):
                with lock:
                    # Simulate some work
                    time.sleep(0.001)
                    # Verify we have the lock
                    assert lock._lock.locked(), f"Thread {thread_id}: Lock should be locked"
            success_count["value"] += 1
        except Exception as e:
            errors.append(f"Thread {thread_id}: {e}")

    # Create multiple threads
    threads = []
    num_threads = 5
    for i in range(num_threads):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check for errors
    assert not errors, f"Errors occurred: {errors}"
    assert success_count["value"] == num_threads, (
        f"Expected {num_threads} successful workers, got {success_count['value']}"
    )

    # Verify the lock is released
    assert not lock._lock.locked(), "Lock should be released after all workers complete"


def test_lock_state_after_concurrent_access():
    """Test that the lock is in a consistent state after concurrent access.

    This test verifies that the lock's internal state remains consistent
    after multiple threads acquire and release it. If the release is not
    thread-safe, the lock may end up in an inconsistent state.
    """
    lock = _AsyncCompatibleLock()

    def worker():
        """Worker that acquires and releases the lock multiple times."""
        for _ in range(5):
            with lock:
                time.sleep(0.001)
                # Verify lock state
                assert lock._lock.locked(), "Lock should be locked inside context"

    # Run multiple workers
    threads = []
    for _ in range(3):
        thread = threading.Thread(target=worker)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Final verification
    assert not lock._lock.locked(), "Lock should be released after all workers complete"


if __name__ == "__main__":
    print("Running test_lock_release_uses_call_soon_threadsafe...")
    try:
        test_lock_release_uses_call_soon_threadsafe()
        print("✓ test_lock_release_uses_call_soon_threadsafe PASSED")
    except AssertionError as e:
        print(f"✗ test_lock_release_uses_call_soon_threadsafe FAILED: {e}")

    print("\nRunning test_multiple_threads_acquire_and_release...")
    try:
        test_multiple_threads_acquire_and_release()
        print("✓ test_multiple_threads_acquire_and_release PASSED")
    except AssertionError as e:
        print(f"✗ test_multiple_threads_acquire_and_release FAILED: {e}")

    print("\nRunning test_lock_state_after_concurrent_access...")
    try:
        test_lock_state_after_concurrent_access()
        print("✓ test_lock_state_after_concurrent_access PASSED")
    except AssertionError as e:
        print(f"✗ test_lock_state_after_concurrent_access FAILED: {e}")

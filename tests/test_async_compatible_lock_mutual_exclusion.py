"""Test mutual exclusion for _AsyncCompatibleLock (Issue #1166).

This test verifies that _AsyncCompatibleLock provides proper mutual exclusion
between synchronous and asynchronous code paths.
"""

import asyncio
import threading
import time
from flywheel.storage import _AsyncCompatibleLock


def test_mutual_exclusion_between_sync_and_async():
    """Test that sync and async code cannot simultaneously hold the lock.

    This test creates a scenario where:
    1. A synchronous thread acquires the lock and holds it
    2. An asynchronous task tries to acquire the same lock
    3. The async task should block until the sync thread releases the lock

    If the lock uses separate underlying locks (threading.Lock and asyncio.Lock),
    both will acquire their respective locks simultaneously, violating mutual
    exclusion.
    """
    lock = _AsyncCompatibleLock()
    results = {"sync_acquired": False, "async_acquired": False}
    sync_ready = threading.Event()
    async_ready = asyncio.Event()

    def sync_worker():
        """Synchronous worker that acquires and holds the lock."""
        with lock:
            results["sync_acquired"] = True
            sync_ready.set()  # Signal that we've acquired the lock
            # Hold the lock for a while to give async a chance to try acquiring
            time.sleep(0.5)
            # Check if async also acquired (should not happen with proper mutex)
            if results["async_acquired"]:
                results["violation"] = "Async acquired while sync held lock"

    async def async_worker():
        """Asynchronous worker that tries to acquire the same lock."""
        await asyncio.sleep(0.1)  # Give sync time to acquire first
        async_ready.set()
        async with lock:
            results["async_acquired"] = True
            # If we get here while sync still holds, we have a violation

    # Run sync worker in a thread
    sync_thread = threading.Thread(target=sync_worker)
    sync_thread.start()

    # Wait for sync to acquire, then run async worker
    sync_ready.wait()
    asyncio.run(async_worker())

    # Wait for sync thread to complete
    sync_thread.join()

    # Verify no violation occurred
    assert not results.get("violation"), (
        f"Mutual exclusion violated: {results['violation']}"
    )


def test_concurrent_sync_and_async_access():
    """Test that concurrent sync and async access properly serializes.

    This test uses a shared counter to verify that only one context
    can modify it at a time.
    """
    lock = _AsyncCompatibleLock()
    counter = {"value": 0}
    errors = []

    def sync_worker():
        """Synchronous worker that increments the counter."""
        try:
            for _ in range(100):
                with lock:
                    current = counter["value"]
                    time.sleep(0.0001)  # Simulate some work
                    counter["value"] = current + 1
        except Exception as e:
            errors.append(f"Sync error: {e}")

    async def async_worker():
        """Asynchronous worker that increments the counter."""
        try:
            for _ in range(100):
                async with lock:
                    current = counter["value"]
                    await asyncio.sleep(0.0001)  # Simulate some work
                    counter["value"] = current + 1
        except Exception as e:
            errors.append(f"Async error: {e}")

    # Run both workers concurrently
    sync_thread = threading.Thread(target=sync_worker)
    sync_thread.start()

    asyncio.run(async_worker())

    sync_thread.join()

    # Check for errors
    assert not errors, f"Errors occurred: {errors}"

    # Verify final count (should be 200 if no race conditions)
    expected = 200
    actual = counter["value"]
    assert actual == expected, (
        f"Counter mismatch: expected {expected}, got {actual}. "
        "This indicates a race condition - sync and async code "
        "were able to modify the counter simultaneously."
    )


if __name__ == "__main__":
    print("Running test_mutual_exclusion_between_sync_and_async...")
    try:
        test_mutual_exclusion_between_sync_and_async()
        print("✓ test_mutual_exclusion_between_sync_and_async PASSED")
    except AssertionError as e:
        print(f"✗ test_mutual_exclusion_between_sync_and_async FAILED: {e}")

    print("\nRunning test_concurrent_sync_and_async_access...")
    try:
        test_concurrent_sync_and_async_access()
        print("✓ test_concurrent_sync_and_async_access PASSED")
    except AssertionError as e:
        print(f"✗ test_concurrent_sync_and_async_access FAILED: {e}")

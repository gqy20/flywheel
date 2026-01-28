"""Test for lock timeout issues under high contention (Issue #1291).

This test verifies that the _AsyncCompatibleLock can handle high contention
scenarios without causing spurious crashes due to timeout issues.

The issue: When the lock is held by another thread (e.g., a long-running async
operation), a synchronous `with` statement will timeout after 1s. While this
prevents indefinite blocking, it turns a potential concurrency bottleneck into
a failure condition. If the lock is frequently contended, this will cause
spurious crashes.

The fix: Increased the timeout from 1s to 10s to handle high-load scenarios
better and prevent spurious crashes under high contention.
"""

import asyncio
import threading
import time

from flywheel.storage import _AsyncCompatibleLock


def test_lock_timeout_under_high_contention():
    """Test that lock doesn't timeout under high contention.

    This test simulates a high-contention scenario where multiple threads
    are trying to acquire the lock while another async operation holds it.

    The current implementation has a 1-second timeout which can cause
    spurious failures under high load. This test verifies that the lock
    can handle reasonable contention without timing out.
    """
    lock = _AsyncCompatibleLock()

    # Track results
    results = {
        "timeouts": 0,
        "successful_acquisitions": 0,
        "errors": 0,
    }
    results_lock = threading.Lock()

    # Simulate a long-running async operation that holds the lock
    async def long_running_async_operation():
        """Simulate a long-running async operation."""
        async with lock:
            # Hold the lock for 2 seconds to simulate a real operation
            await asyncio.sleep(2)

    # Function to run the async operation in a thread with event loop
    def run_async_operation():
        """Run the async operation in a dedicated event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(long_running_async_operation())
        finally:
            loop.close()

    # Start the async operation in a background thread
    async_thread = threading.Thread(target=run_async_operation)
    async_thread.start()

    # Give the async thread time to acquire the lock
    time.sleep(0.5)

    # Now try to acquire the lock from multiple threads
    # In a high-contention scenario, these should wait but not timeout
    def try_acquire_lock(thread_id):
        """Try to acquire the lock from a synchronous context."""
        nonlocal results
        try:
            with lock:
                # If we get here, the lock was acquired successfully
                # This should work even if we had to wait
                with results_lock:
                    results["successful_acquisitions"] += 1
        except TimeoutError as e:
            # This indicates a timeout - this is the bug we're testing for
            with results_lock:
                results["timeouts"] += 1
                print(f"Thread {thread_id}: Timeout - {e}")
        except Exception as e:
            with results_lock:
                results["errors"] += 1
                print(f"Thread {thread_id}: Error - {e}")

    # Try to acquire from multiple threads
    threads = []
    num_threads = 5
    for i in range(num_threads):
        thread = threading.Thread(target=try_acquire_lock, args=(i,))
        threads.append(thread)
        thread.start()
        # Small delay between thread starts to simulate real contention
        time.sleep(0.2)

    # Wait for all threads to complete
    for thread in threads:
        thread.join(timeout=15)
        if thread.is_alive():
            with results_lock:
                results["timeouts"] += 1

    # Wait for the async thread to complete
    async_thread.join(timeout=10)

    # Verify results
    # After the fix (10-second timeout), we expect no timeouts
    print(f"\nTest Results:")
    print(f"  Timeouts: {results['timeouts']}")
    print(f"  Successful acquisitions: {results['successful_acquisitions']}")
    print(f"  Errors: {results['errors']}")

    # After the fix (10-second timeout), there should be no timeouts
    # All threads should successfully acquire the lock
    assert results['timeouts'] == 0, (
        f"Expected no timeouts with 10-second timeout, but got {results['timeouts']}. "
        "This indicates the fix for Issue #1291 is not working correctly."
    )
    assert results['successful_acquisitions'] == num_threads, (
        f"Expected {num_threads} successful acquisitions, but got {results['successful_acquisitions']}. "
        "This indicates some threads failed to acquire the lock."
    )
    assert results['errors'] == 0, (
        f"Expected no errors, but got {results['errors']}. "
        f"Errors: {results}"
    )


def test_lock_timeout_with_long_async_operation():
    """Test lock behavior when async operation holds lock for extended time.

    This test verifies the specific scenario mentioned in Issue #1291:
    If the lock is held by another thread (e.g., a long-running async operation),
    a synchronous `with` statement will timeout.
    """
    lock = _AsyncCompatibleLock()

    # Track if timeout occurred
    timeout_occurred = [False]
    acquisition_time = [None]

    # Simulate a long-running async operation (3 seconds)
    async def long_async_operation():
        """Hold the lock for 3 seconds."""
        async with lock:
            await asyncio.sleep(3)

    def run_async_operation():
        """Run async operation in background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(long_async_operation())
        finally:
            loop.close()

    # Start the async operation
    async_thread = threading.Thread(target=run_async_operation)
    async_thread.start()

    # Give it time to acquire the lock
    time.sleep(0.5)

    # Now try to acquire from sync context
    start_time = time.time()
    try:
        with lock:
            acquisition_time[0] = time.time() - start_time
            # If we get here, the lock was acquired successfully
            print(f"Lock acquired after {acquisition_time[0]:.2f}s")
    except TimeoutError as e:
        timeout_occurred[0] = True
        acquisition_time[0] = time.time() - start_time
        print(f"Timeout occurred after {acquisition_time[0]:.2f}s: {e}")

    # Wait for async thread to complete
    async_thread.join(timeout=10)

    # Document current behavior
    print(f"\nTest Results:")
    print(f"  Timeout occurred: {timeout_occurred[0]}")
    print(f"  Time waited: {acquisition_time[0]:.2f}s")

    # After the fix (10-second timeout), this should succeed without timeout
    # The async operation holds the lock for 3 seconds, which is less than 10 seconds
    assert not timeout_occurred[0], (
        f"Expected no timeout with 10-second timeout, but timeout occurred after {acquisition_time[0]:.2f}s. "
        "This indicates the fix for Issue #1291 is not working correctly."
    )
    assert acquisition_time[0] >= 3, (
        f"Expected to wait at least 3 seconds (duration of async operation), "
        f"but only waited {acquisition_time[0]:.2f}s. "
        "This indicates the lock was not properly held by the async operation."
    )


if __name__ == "__main__":
    print("Testing lock timeout under high contention...")
    test_lock_timeout_under_high_contention()

    print("\nTesting lock timeout with long async operation...")
    test_lock_timeout_with_long_async_operation()

    print("\n✅ All tests passed - Issue #1291 is fixed!")

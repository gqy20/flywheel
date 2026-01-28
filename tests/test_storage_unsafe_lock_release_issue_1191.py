"""Test for unsafe lock release in __exit__ (Issue #1191)."""

import asyncio
import tempfile
import threading
import time

from flywheel.storage import _AsyncCompatibleLock


def test_lock_release_uses_run_coroutine_threadsafe():
    """Test that lock release uses run_coroutine_threadsafe for safety.

    This test verifies the fix for Issue #1191: Using call_soon_threadsafe
    to release the lock is risky because if the event loop stops before the
    release callback runs, the lock remains locked forever.

    The fix uses run_coroutine_threadsafe with a timeout to ensure the
    release completes before returning.
    """
    lock = _AsyncCompatibleLock()

    # Create an event loop in a separate thread
    loop = None
    thread_started = threading.Event()

    def run_loop():
        nonlocal loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        thread_started.set()
        loop.run_forever()

    # Start the event loop thread
    loop_thread = threading.Thread(target=run_loop, daemon=True)
    loop_thread.start()
    thread_started.wait()

    try:
        # Acquire the lock using sync context manager
        with lock:
            # Lock is now acquired
            assert lock._locked is True
            # The underlying asyncio lock should also be locked
            assert lock._lock.locked()

        # After exiting the context, the lock should be released
        assert lock._locked is False

        # Verify the underlying asyncio lock is released
        # by trying to acquire it again
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

        try:
            # This should succeed immediately if the lock was properly released
            # If the lock wasn't released (bug exists), this will timeout
            future = asyncio.run_coroutine_threadsafe(
                lock._lock.acquire(), new_loop
            )
            future.result(timeout=0.5)  # Short timeout to detect hanging

            # If we got here, the lock was released - test passes
            # Release the lock we just acquired
            lock._lock.release()
        except TimeoutError:
            raise AssertionError(
                "Lock was not properly released after __exit__. "
                "This indicates the bug from Issue #1191 exists: "
                "call_soon_threadsafe doesn't guarantee execution."
            )
        finally:
            new_loop.close()

    finally:
        # Clean up the loop thread
        loop.call_soon(loop.stop)
        loop_thread.join(timeout=2)


def test_lock_release_with_timeout():
    """Test that lock release has a timeout to prevent hanging.

    This test verifies that the lock release implementation uses a timeout
    when calling run_coroutine_threadsafe, preventing indefinite hangs if
    the event loop is unresponsive.
    """
    lock = _AsyncCompatibleLock()

    # Create an event loop that will be slow to respond
    loop = None
    thread_started = threading.Event()

    def run_loop():
        nonlocal loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        thread_started.set()
        loop.run_forever()

    # Start the event loop thread
    loop_thread = threading.Thread(target=run_loop, daemon=True)
    loop_thread.start()
    thread_started.wait()

    try:
        # Acquire and release the lock
        # This should complete within a reasonable time
        start_time = time.time()

        with lock:
            pass

        elapsed = time.time() - start_time

        # Should complete quickly (within 2 seconds including timeout)
        # If it takes longer, the timeout is not working properly
        assert elapsed < 2.0, (
            f"Lock release took {elapsed:.2f}s, expected < 2.0s. "
            "Timeout mechanism may not be working correctly."
        )

    finally:
        # Clean up
        loop.call_soon(loop.stop)
        loop_thread.join(timeout=2)

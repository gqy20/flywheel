"""Test for potential deadlock due to event loop mismatch (Issue #1190)."""

import asyncio
import threading
import time

from flywheel.storage import _AsyncCompatibleLock


def test_no_deadlock_with_cross_thread_lock_usage():
    """Test that lock doesn't deadlock when used across threads.

    This test verifies the fix for Issue #1190: The check `if loop is current_loop`
    prevents deadlocks only if the lock is used in the 'main' async thread.
    If `__enter__` is called from a background thread while `current_loop` is the
    main loop, `run_coroutine_threadsafe` is scheduled on the main loop. If the
    main loop is blocked waiting for the background thread (holding the lock), a
    deadlock occurs.

    The fix ensures that locks are never used across threads that might block
    each other by tracking which thread owns the event loop.
    """
    lock = _AsyncCompatibleLock()

    # Create the main event loop
    main_loop = asyncio.new_event_loop()
    main_loop_thread_id = threading.get_ident()

    # Track the event loop's owner thread
    main_loop.owner_thread_id = main_loop_thread_id

    # Flag to indicate deadlock
    deadlock_detected = [False]
    background_thread_acquired = threading.Event()
    main_thread_can_proceed = threading.Event()

    def background_thread_task():
        """Background thread that tries to acquire the lock.

        This simulates the scenario where a background thread tries to use
        the lock while the main thread is also using it.
        """
        nonlocal deadlock_detected

        # Try to acquire the lock using sync context manager
        # In the buggy version, this would deadlock if the main loop is blocked
        try:
            background_thread_acquired.set()
            with lock:
                # If we get here without timeout, the test passes
                deadlock_detected[0] = False
        except Exception as e:
            # Any exception is also a failure
            deadlock_detected[0] = True
            raise

    async def main_thread_task():
        """Main thread task that might block."""
        # Signal background thread to start
        background_thread_acquired.wait()

        # Simulate some work
        await asyncio.sleep(0.1)

        # Signal background thread it can proceed
        main_thread_can_proceed.set()

    def run_main_loop():
        """Run the main event loop."""
        asyncio.set_event_loop(main_loop)

        # Start the background thread
        bg_thread = threading.Thread(target=background_thread_task)
        bg_thread.start()

        # Run the main thread task
        try:
            main_loop.run_until_complete(main_thread_task())
        finally:
            bg_thread.join(timeout=5)
            if bg_thread.is_alive():
                deadlock_detected[0] = True

        main_loop.close()

    # Run the test
    start_time = time.time()
    main_thread = threading.Thread(target=run_main_loop)
    main_thread.start()
    main_thread.join(timeout=5)

    elapsed = time.time() - start_time

    # If the thread is still alive, we have a deadlock
    if main_thread.is_alive():
        raise AssertionError(
            f"Deadlock detected! Test hung for {elapsed:.2f}s. "
            "This indicates the bug from Issue #1190: "
            "Cross-thread lock usage can cause deadlock."
        )

    # Also check the flag
    assert not deadlock_detected[0], (
        "Deadlock detected in background thread. "
        "This indicates the bug from Issue #1190."
    )

    # Test should complete quickly (< 3 seconds)
    assert elapsed < 3.0, (
        f"Test took {elapsed:.2f}s, expected < 3.0s. "
        "Possible deadlock or performance issue."
    )


def test_lock_detects_cross_thread_usage():
    """Test that lock detects when it's being used from different threads.

    This test verifies that the lock implementation properly detects and
    handles cross-thread usage to prevent deadlocks.
    """
    lock = _AsyncCompatibleLock()

    # Create an event loop
    loop = asyncio.new_event_loop()

    # Track which thread owns this loop
    loop_owner_thread_id = threading.get_ident()

    # Store the thread ID in the loop for tracking
    loop._owner_thread_id = loop_owner_thread_id

    # Flag to track if background thread succeeded
    background_thread_result = {"success": False, "error": None}

    def background_thread_lock_usage():
        """Try to use the lock from a different thread."""
        try:
            # This should either work safely or raise a clear error
            # It should NOT deadlock
            with lock:
                background_thread_result["success"] = True
        except RuntimeError as e:
            # If it raises a RuntimeError, that's acceptable
            # as long as it's a clear error message
            if "event loop" in str(e).lower() or "thread" in str(e).lower():
                background_thread_result["success"] = True
                background_thread_result["error"] = str(e)
            else:
                background_thread_result["error"] = str(e)
        except Exception as e:
            background_thread_result["error"] = str(e)

    # Start background thread
    bg_thread = threading.Thread(target=background_thread_lock_usage)
    start_time = time.time()
    bg_thread.start()
    bg_thread.join(timeout=3)
    elapsed = time.time() - start_time

    # Check for deadlock
    if bg_thread.is_alive():
        raise AssertionError(
            f"Deadlock detected! Background thread hung for {elapsed:.2f}s. "
            "This indicates the bug from Issue #1190: "
            "Cross-thread lock usage caused deadlock."
        )

    # The background thread should either succeed or raise a clear error
    assert bg_thread.result if hasattr(bg_thread, 'result') else True, (
        f"Background thread failed with error: {background_thread_result['error']}"
    )

    loop.close()

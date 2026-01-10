"""Test for Issue #1285 - Race condition in _get_or_create_loop.

This test verifies that the event loop is fully initialized and ready
before other threads try to use it.
"""

import threading
import time
import asyncio
import pytest
from flywheel.storage import _AsyncCompatibleLock


def test_loop_thread_ready_before_use():
    """Test that the event loop thread is ready before other threads use it.

    This test creates multiple threads that all try to acquire the lock
    simultaneously. The test verifies that:
    1. The event loop is fully initialized
    2. The loop thread is running
    3. Other threads can safely use run_coroutine_threadsafe

    This is a regression test for Issue #1285.
    """
    lock = _AsyncCompatibleLock()
    errors = []
    success_count = [0]
    num_threads = 10

    def acquire_lock(thread_id):
        """Try to acquire the lock in a thread."""
        try:
            # Small random delay to increase chance of hitting race condition
            time.sleep(0.001 * thread_id)

            # Try to acquire the lock synchronously
            with lock:
                # If we got here without error, the loop is ready
                success_count[0] += 1
        except Exception as e:
            errors.append((thread_id, str(e)))

    # Create and start multiple threads that all try to use the lock
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=acquire_lock, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=5)

    # All threads should succeed
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert success_count[0] == num_threads, f"Expected {num_threads} successes, got {success_count[0]}"


def test_event_loop_thread_running_before_return():
    """Test that the event loop thread is running when _get_or_create_loop returns.

    This test directly checks that after calling _get_or_create_loop,
    the event loop thread is alive and the loop is running.
    """
    lock = _AsyncCompatibleLock()

    # Call _get_or_create_loop to initialize the loop
    loop = lock._get_or_create_loop()

    # Verify the loop is set
    assert loop is not None, "Event loop should not be None"

    # Verify the loop thread is alive
    assert lock._loop_thread is not None, "Loop thread should not be None"
    assert lock._loop_thread.is_alive(), "Loop thread should be alive"

    # Verify the event loop is actually running (not closed)
    assert not loop.is_closed(), "Event loop should not be closed"

    # Verify we can schedule work on the loop
    def dummy_task():
        return "success"

    future = asyncio.run_coroutine_threadsafe(
        asyncio.coroutine(dummy_task)(), loop
    )
    # This should not raise or timeout
    result = future.result(timeout=1)
    assert result == "success"


def test_concurrent_initialization():
    """Test concurrent initialization from multiple threads.

    This test simulates the exact race condition described in Issue #1285:
    Multiple threads call _get_or_create_loop concurrently, and one thread
    should create the loop while others wait for it to be fully ready.
    """
    lock = _AsyncCompatibleLock()
    loops = []
    errors = []
    num_threads = 20

    def get_loop(thread_id):
        """Try to get or create the event loop."""
        try:
            # Small delay to increase race condition likelihood
            time.sleep(0.0001 * thread_id)
            loop = lock._get_or_create_loop()
            loops.append(loop)

            # Verify the loop is usable
            if not lock._loop_thread.is_alive():
                errors.append((thread_id, "Loop thread not alive"))

            if loop.is_closed():
                errors.append((thread_id, "Loop is closed"))
        except Exception as e:
            errors.append((thread_id, str(e)))

    # Start all threads simultaneously
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=get_loop, args=(i,))
        threads.append(t)

    # Start all at once
    for t in threads:
        t.start()

    # Wait for completion
    for t in threads:
        t.join(timeout=5)

    # All threads should get the same loop
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(loops) == num_threads, f"Expected {num_threads} loops, got {len(loops)}"

    # All should be the same loop object
    first_loop = loops[0]
    for loop in loops[1:]:
        assert loop is first_loop, "All threads should get the same loop object"

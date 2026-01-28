"""Test for resource cleanup in _AsyncCompatibleLock (Issue #1256).

This test verifies that _AsyncCompatibleLock properly cleans up resources
(event loop, background thread, stop event) when close() is called or when
the object is garbage collected via __del__.

Issue #1256: 潜在的内存泄漏与资源未释放
The concern was that the class creates background threads and event loops
but may not properly close them, causing resource leaks. This test verifies
that the close() method and __del__ destructor properly clean up all resources.
"""

import asyncio
import threading
import time
import gc
import weakref

from flywheel.storage import _AsyncCompatibleLock


def test_close_cleanup_event_loop():
    """Test that close() properly cleans up the event loop.

    Verifies that after calling close(), the event loop is closed and
    all resources are released.
    """
    lock = _AsyncCompatibleLock()

    # Use the lock to trigger event loop creation
    try:
        with lock:
            # Do some work
            time.sleep(0.01)
    except TimeoutError:
        pass

    # Verify event loop was created
    assert lock._event_loop is not None, "Event loop should be created after lock usage"
    assert lock._loop_thread is not None, "Background thread should be created"

    # Save references for verification
    event_loop = lock._event_loop
    loop_thread = lock._loop_thread
    stop_event = lock._loop_thread_stop_event

    # Call close to clean up resources
    lock.close()

    # Verify all resources are cleaned up
    assert lock._event_loop is None, "Event loop should be set to None"
    assert lock._event_loop_thread_id is None, "Event loop thread ID should be set to None"
    assert lock._loop_thread is None, "Loop thread should be set to None"
    assert lock._loop_thread_stop_event is None, "Stop event should be set to None"

    # Verify the event loop is actually closed
    assert event_loop.is_closed(), "Event loop should be closed"

    # Verify stop event was set
    assert stop_event.is_set(), "Stop event should be set to signal thread to stop"

    # Give thread time to finish
    if loop_thread.is_alive():
        loop_thread.join(timeout=1.0)
    assert not loop_thread.is_alive(), "Background thread should have stopped"


def test_close_idempotent():
    """Test that close() can be called multiple times safely.

    Verifies that calling close() multiple times doesn't raise errors
    and properly handles the idempotent case.
    """
    lock = _AsyncCompatibleLock()

    # Use the lock to trigger event loop creation
    try:
        with lock:
            time.sleep(0.01)
    except TimeoutError:
        pass

    # Call close multiple times
    lock.close()
    lock.close()
    lock.close()

    # Should not raise any errors
    assert lock._event_loop is None


def test_close_before_use():
    """Test that close() works even if the lock was never used.

    Verifies that calling close() on an unused lock (no event loop created)
    doesn't raise errors.
    """
    lock = _AsyncCompatibleLock()

    # Close without using the lock
    lock.close()

    # Should not raise any errors
    assert lock._event_loop is None
    assert lock._loop_thread is None


def test_del_cleanup():
    """Test that __del__ properly cleans up resources.

    Verifies that when the lock object is garbage collected,
    resources are properly cleaned up via __del__.
    """
    # Create a lock in a function so it goes out of scope
    def create_and_use_lock():
        lock = _AsyncCompatibleLock()

        # Use the lock to trigger event loop creation
        try:
            with lock:
                time.sleep(0.01)
        except TimeoutError:
            pass

        # Save weak references to check cleanup
        loop = lock._event_loop
        thread = lock._loop_thread
        stop_event = lock._loop_thread_stop_event

        return weakref.ref(lock), loop, thread, stop_event

    weak_ref, event_loop, loop_thread, stop_event = create_and_use_lock()

    # Delete the lock
    del weak_ref

    # Force garbage collection
    gc.collect()

    # Give time for cleanup
    time.sleep(0.5)

    # Verify event loop was closed
    # Note: The event loop object might still exist but should be closed
    assert event_loop.is_closed(), "Event loop should be closed after __del__"

    # Verify stop event was set
    assert stop_event.is_set(), "Stop event should be set"

    # Verify thread has stopped
    if loop_thread.is_alive():
        loop_thread.join(timeout=1.0)
    assert not loop_thread.is_alive(), "Background thread should have stopped"


def test_context_manager_with_close():
    """Test that close() works correctly after using context manager.

    Verifies that resources are properly cleaned up when close() is called
    after the lock has been used in a context manager.
    """
    lock = _AsyncCompatibleLock()

    # Use the lock multiple times
    for i in range(3):
        try:
            with lock:
                time.sleep(0.01)
        except TimeoutError:
            pass

    # Now close it
    lock.close()

    # Verify cleanup
    assert lock._event_loop is None
    assert lock._loop_thread is None


def test_multiple_locks_cleanup():
    """Test that multiple locks can be cleaned up independently.

    Verifies that creating and closing multiple locks doesn't interfere
    with each other's cleanup.
    """
    locks = [_AsyncCompatibleLock() for _ in range(5)]

    # Use all locks
    for lock in locks:
        try:
            with lock:
                time.sleep(0.01)
        except TimeoutError:
            pass

    # Close all locks
    for lock in locks:
        lock.close()

    # Verify all are cleaned up
    for lock in locks:
        assert lock._event_loop is None
        assert lock._loop_thread is None


def test_async_context_cleanup():
    """Test that close() works after using async context manager.

    Verifies that resources are cleaned up properly when the lock is used
    in an async context.
    """
    async def use_lock_async():
        lock = _AsyncCompatibleLock()

        async with lock:
            await asyncio.sleep(0.01)

        # Now close it
        lock.close()

        # Verify cleanup
        assert lock._event_loop is None
        assert lock._loop_thread is None

    # Run the async test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(use_lock_async())
    finally:
        loop.close()


def test_no_resource_leak_after_close():
    """Test that there's no resource leak after calling close().

    Verifies that the background thread is actually stopped and doesn't
    continue running after close() is called.
    """
    lock = _AsyncCompatibleLock()

    # Track if the background thread is still running
    thread_alive_after_close = [False]

    # Use the lock to trigger event loop creation
    try:
        with lock:
            time.sleep(0.01)
    except TimeoutError:
        pass

    # Get the background thread
    loop_thread = lock._loop_thread

    # Close the lock
    lock.close()

    # Check if thread is still alive
    thread_alive_after_close[0] = loop_thread.is_alive()

    # Give thread time to finish
    loop_thread.join(timeout=1.0)

    # Verify thread stopped
    assert not thread_alive_after_close[0] or not loop_thread.is_alive(), (
        "Background thread should stop after close() is called"
    )

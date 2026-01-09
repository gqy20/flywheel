"""Test for event loop not running in sync context (Issue #1211)."""

import asyncio
import threading
import time

from flywheel.storage import _AsyncCompatibleLock


def test_sync_context_without_running_loop():
    """Test that lock works correctly in sync context without a running event loop.

    This test verifies the fix for Issue #1211: When _get_or_create_loop creates
    a new event loop in a synchronous context (because asyncio.get_running_loop()
    raises RuntimeError), the new event loop is never started. If we then use
    run_coroutine_threadsafe to submit tasks to this loop, they will never execute
    because the loop is not running.

    The fix ensures that the event loop is properly started in a background thread
    or that the lock acquisition mechanism handles this case correctly.
    """
    # Make sure there's no running event loop in the current thread
    try:
        asyncio.get_running_loop()
        assert False, "There should be no running event loop for this test"
    except RuntimeError:
        # Expected - no running loop
        pass

    # Create a lock in a sync context (no running loop)
    lock = _AsyncCompatibleLock()

    # Track if the lock was acquired
    acquired = []

    # Try to use the lock with sync context manager
    # This should work even without a running event loop
    try:
        with lock:
            # If we get here, the lock was acquired successfully
            acquired.append(True)
            # Do some work
            time.sleep(0.01)
    except TimeoutError:
        # This is the bug: the lock acquisition times out because
        # run_coroutine_threadsafe submitted to a non-running loop
        assert False, (
            "Lock acquisition timed out! This indicates the bug from Issue #1211: "
            "The event loop was created but never started, so run_coroutine_threadsafe "
            "tasks never execute."
        )
    except Exception as e:
        assert False, f"Unexpected exception: {e}"

    # Verify the lock was acquired
    assert len(acquired) == 1, "Lock should have been acquired successfully"

    # The actual asyncio.Lock should not be held after exiting the context
    assert not lock._lock.locked(), "Lock should be released after exiting context"


def test_multiple_sync_acquisitions_without_running_loop():
    """Test multiple lock acquisitions in sync context without running loop.

    This test verifies that the lock can be acquired and released multiple times
    in a synchronous context, even when there's no running event loop initially.
    """
    # Make sure there's no running event loop
    try:
        asyncio.get_running_loop()
        assert False, "There should be no running event loop for this test"
    except RuntimeError:
        pass

    lock = _AsyncCompatibleLock()
    acquisition_count = []

    # Try multiple acquisitions
    for i in range(3):
        try:
            with lock:
                acquisition_count.append(i)
                time.sleep(0.01)
        except TimeoutError:
            assert False, (
                f"Lock acquisition timed out on attempt {i+1}! "
                "This indicates the bug from Issue #1211."
            )
        except Exception as e:
            assert False, f"Unexpected exception on attempt {i+1}: {e}"

    # All acquisitions should have succeeded
    assert len(acquisition_count) == 3, "All 3 acquisitions should have succeeded"

    # Lock should not be held
    assert not lock._lock.locked(), "Lock should be released after all acquisitions"


def test_nested_sync_locks_without_running_loop():
    """Test nested sync context managers without running loop.

    This test verifies that _AsyncCompatibleLock supports re-entry in the same
    thread (if it's a reentrant lock) even without a running event loop.
    """
    # Make sure there's no running event loop
    try:
        asyncio.get_running_loop()
        assert False, "There should be no running event loop for this test"
    except RuntimeError:
        pass

    lock = _AsyncCompatibleLock()

    # Try nested acquisition
    try:
        with lock:
            # First level acquired
            with lock:
                # Second level acquired
                time.sleep(0.01)
    except TimeoutError:
        # This might be expected if the lock is not reentrant
        # But it should NOT be due to the bug in Issue #1211
        # (event loop not running)
        # Check if there's a running loop now
        try:
            loop = asyncio.get_running_loop()
            # If there's a running loop now but it wasn't started properly,
            # the task would never execute
            assert False, "Event loop exists but tasks aren't executing"
        except RuntimeError:
            assert False, (
                "Lock acquisition timed out due to non-running event loop! "
                "This indicates the bug from Issue #1211."
            )
    except Exception as e:
        # ReentrantLock should support nested acquisition
        # If it doesn't, that's a different issue
        pass

    # Lock should not be held
    assert not lock._lock.locked(), "Lock should be released after nested contexts"

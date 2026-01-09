"""Test for Issue #1200 - Deadlock risk in __enter__ due to event loop thread mismatch

This test validates that the _AsyncCompatibleLock properly prevents deadlock scenarios
that can occur when using run_coroutine_threadsafe for synchronous lock acquisition.

The issue is that run_coroutine_threadsafe can create deadlocks when:
1. The event loop is running in a different thread
2. That thread is blocked waiting for a resource held by the current thread
3. The current thread is waiting for the lock acquisition via run_coroutine_threadsafe

The fix (implemented in Issue #1190) enforces strict thread affinity by checking
if the current thread matches the event loop thread before attempting to use
run_coroutine_threadsafe.
"""

import asyncio
import threading
import time
import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_cross_thread_lock_acquisition_should_fail_fast():
    """
    Test that acquiring a lock from a different thread than the event loop owner
    fails immediately with a RuntimeError rather than causing a potential deadlock.

    This is the primary fix for Issue #1200 - strict thread affinity enforcement.
    """
    # Create a lock with an event loop
    lock = _AsyncCompatibleLock()

    # Start an event loop in a separate thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    event_loop_thread = threading.Thread(
        target=loop.run_forever,
        daemon=True
    )
    event_loop_thread.start()

    try:
        # Register the event loop with the lock
        # This will record the event loop's thread ID
        lock.register_event_loop(loop)

        # Give the event loop thread time to start
        time.sleep(0.1)

        # Try to acquire from a different thread
        # This should raise RuntimeError immediately due to thread mismatch check
        # This prevents the deadlock scenario described in Issue #1200
        different_thread_result = []

        def acquire_from_different_thread():
            try:
                with lock:
                    different_thread_result.append("acquired")
            except RuntimeError as e:
                different_thread_result.append("runtime_error")
                # Verify the error message mentions thread mismatch
                assert "different thread" in str(e).lower() or "event loop thread" in str(e).lower()

        # Run acquisition from a different thread
        t = threading.Thread(target=acquire_from_different_thread)
        t.start()
        t.join(timeout=5)

        # Should have failed with RuntimeError (not hung/deadlocked)
        assert len(different_thread_result) == 1
        assert different_thread_result[0] == "runtime_error", \
            f"Expected RuntimeError when acquiring from different thread, got {different_thread_result[0]}"

    finally:
        loop.call_soon_threadsafe(loop.stop)
        event_loop_thread.join(timeout=5)
        loop.close()


def test_same_thread_lock_acquisition_should_work():
    """
    Test that acquiring a lock from the same thread as the event loop works correctly.
    This is the safe usage pattern that should be supported.
    """
    lock = _AsyncCompatibleLock()

    # Create and start event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    event_loop_thread = threading.Thread(
        target=loop.run_forever,
        daemon=True
    )
    event_loop_thread.start()

    try:
        lock.register_event_loop(loop)

        # Give the event loop thread time to start
        time.sleep(0.1)

        # Acquire from the same thread that owns the event loop
        # This should work without raising RuntimeError
        success = []

        def acquire_from_event_loop_thread():
            try:
                with lock:
                    success.append("acquired")
            except Exception as e:
                success.append(f"error: {type(e).__name__}")

        # Acquire from the event loop thread (same thread that owns the loop)
        loop.call_soon_threadsafe(acquire_from_event_loop_thread)

        # Wait for the acquisition to complete
        # With a reasonable timeout to ensure it doesn't deadlock
        timeout = time.time() + 2
        while not success and time.time() < timeout:
            time.sleep(0.01)

        assert len(success) == 1, "Lock acquisition should complete"
        assert success[0] == "acquired", \
            f"Expected successful acquisition, got {success[0]}"

    finally:
        loop.call_soon_threadsafe(loop.stop)
        event_loop_thread.join(timeout=5)
        loop.close()


def test_multiple_locks_cross_thread_should_all_fail_fast():
    """
    Test that multiple locks all enforce thread affinity consistently.

    This validates that the deadlock prevention is applied uniformly across
    all _AsyncCompatibleLock instances.
    """
    locks = [_AsyncCompatibleLock() for _ in range(3)]

    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    event_loop_thread = threading.Thread(
        target=loop.run_forever,
        daemon=True
    )
    event_loop_thread.start()

    try:
        # Register all locks with the same event loop
        for lock in locks:
            lock.register_event_loop(loop)

        time.sleep(0.1)

        # Try to acquire all locks from a different thread
        # All should fail fast with RuntimeError
        results = []

        def acquire_locks_from_different_thread():
            for i, lock in enumerate(locks):
                try:
                    with lock:
                        results.append(f"lock{i}_acquired")
                except RuntimeError:
                    results.append(f"lock{i}_error")

        t = threading.Thread(target=acquire_locks_from_different_thread)
        t.start()
        t.join(timeout=5)

        # All should have failed with RuntimeError
        assert len(results) == 3
        for result in results:
            assert result.endswith("_error"), \
                f"Expected all locks to fail with RuntimeError, got {results}"

    finally:
        loop.call_soon_threadsafe(loop.stop)
        event_loop_thread.join(timeout=5)
        loop.close()

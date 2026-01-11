"""Test _async_event_init_lock acquisition in __aexit__ (Issue #1436).

This test verifies that __aexit__ acquires _async_event_init_lock before
accessing _async_events to prevent race conditions.
"""

import asyncio
import threading
import time
from flywheel.storage import _AsyncCompatibleLock


def test_aexit_acquires_async_event_init_lock():
    """Test that __aexit__ acquires _async_event_init_lock before signaling events.

    This test creates a race condition scenario:
    1. One thread is in the middle of __aexit__, about to iterate over _async_events
    2. Another thread simultaneously modifies _async_events

    If __aexit__ doesn't hold _async_event_init_lock, we can get a RuntimeError
    from WeakKeyDictionary being modified during iteration.
    """
    lock = _AsyncCompatibleLock()
    errors = []
    iteration_started = threading.Event()
    modify_ready = threading.Event()

    # First, populate _async_events by getting an async event
    async def setup_async_event():
        async with lock:
            pass
    asyncio.run(setup_async_event())

    # Track if __aexit__ is protected by _async_event_init_lock
    aexit_in_progress = {"value": False}
    modification_attempted = {"value": False}

    def sync_exit_worker():
        """Worker that enters and exits the lock synchronously."""
        try:
            # Acquire and release the lock, which triggers __exit__
            # (which should use _async_event_init_lock)
            with lock:
                pass
        except Exception as e:
            errors.append(f"Sync exit error: {type(e).__name__}: {e}")

    async def async_exit_worker():
        """Worker that enters and exits the lock asynchronously.

        This will trigger __aexit__, which should also acquire
        _async_event_init_lock before accessing _async_events.
        """
        try:
            async with lock:
                pass
        except Exception as e:
            errors.append(f"Async exit error: {type(e).__name__}: {e}")

    def concurrent_get_async_event():
        """Worker that concurrently calls _get_async_event.

        This modifies _async_events under _async_event_init_lock.
        If __aexit__ doesn't hold the lock, we can get race conditions.
        """
        try:
            # Try to get/create async event while another context is exiting
            async def get_event():
                # This will modify _async_events
                lock._get_async_event()
            asyncio.run(get_event())
        except Exception as e:
            errors.append(f"Get event error: {type(e).__name__}: {e}")

    # Run many concurrent iterations to increase chance of catching race condition
    def stress_test_iteration():
        """Run a single iteration of the stress test."""
        threads = []

        # Start sync exit thread
        t1 = threading.Thread(target=sync_exit_worker)
        t1.start()
        threads.append(t1)

        # Start async exit thread (in its own event loop)
        t2 = threading.Thread(target=lambda: asyncio.run(async_exit_worker()))
        t2.start()
        threads.append(t2)

        # Start multiple concurrent get_event threads
        for _ in range(5):
            t = threading.Thread(target=concurrent_get_async_event)
            t.start()
            threads.append(t)

        # Wait for all threads
        for t in threads:
            t.join(timeout=5)
            if t.is_alive():
                errors.append("Thread timeout - possible deadlock")

    # Run many iterations
    for i in range(50):
        stress_test_iteration()
        if errors:
            break

    # Check for errors
    assert not errors, (
        f"Race condition detected in iteration {i+1}:\n" +
        "\n".join(errors)
    )

    print("✓ No race conditions detected after 50 stress test iterations")


def test_aexit_protects_async_events_iteration():
    """Test that __aexit__ properly protects _async_events iteration.

    This is a more direct test that verifies the lock is held.
    """
    lock = _AsyncCompatibleLock()

    # Populate _async_events with multiple event loops
    async def create_events():
        async with lock:
            pass

    # Create events in different "event loops" (simulated by sequential runs)
    for _ in range(10):
        asyncio.run(create_events())

    # Now trigger __aexit__ while another thread tries to modify _async_events
    errors = []

    def trigger_aexit():
        try:
            asyncio.run(create_events())
        except Exception as e:
            errors.append(f"__aexit__ error: {type(e).__name__}: {e}")

    def modify_async_events():
        try:
            # Directly access _async_events to simulate concurrent modification
            # (this would normally be protected by _async_event_init_lock)
            with lock._async_event_init_lock:
                # Create a copy to trigger potential issues
                _ = list(lock._async_events.values())
        except Exception as e:
            errors.append(f"Modification error: {type(e).__name__}: {e}")

    # Run concurrent operations
    threads = []
    for _ in range(20):
        t1 = threading.Thread(target=trigger_aexit)
        t2 = threading.Thread(target=modify_async_events)
        t1.start()
        t2.start()
        threads.extend([t1, t2])

    for t in threads:
        t.join(timeout=2)
        if t.is_alive():
            errors.append("Thread timeout")

    assert not errors, f"Errors during concurrent access:\n" + "\n".join(errors)
    print("✓ __aexit__ properly protected _async_events iteration")


if __name__ == "__main__":
    print("Testing Issue #1436: __aexit__ should acquire _async_event_init_lock\n")

    print("Test 1: Stress test for race condition...")
    try:
        test_aexit_acquires_async_event_init_lock()
    except AssertionError as e:
        print(f"✗ FAILED: {e}")

    print("\nTest 2: Direct iteration protection test...")
    try:
        test_aexit_protects_async_events_iteration()
    except AssertionError as e:
        print(f"✗ FAILED: {e}")

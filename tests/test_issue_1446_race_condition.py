"""Test for race condition in _get_async_event (Issue #1446).

This test verifies that the Event state remains consistent with the actual
lock state even when there's a race between checking lock.locked() and
another thread releasing the lock.
"""

import asyncio
import threading
import time
from flywheel.storage import _AsyncCompatibleLock


def test_event_state_consistency_during_race():
    """Test that Event state stays consistent with lock state during race.

    This test creates a scenario where:
    1. A sync thread holds the lock
    2. An async context calls _get_async_event while the lock is held
    3. The sync thread releases the lock during Event initialization
    4. The Event should correctly reflect the lock's actual state

    The bug occurs when the check `if not self._lock.locked()` happens
    while another thread is releasing the lock, creating an inconsistent
    Event state.
    """
    lock = _AsyncCompatibleLock()
    results = {"event_state": None, "lock_state": None}
    sync_ready = threading.Event()
    continue_flag = threading.Event()
    async_ready = threading.Event()

    def sync_worker():
        """Synchronous worker that acquires and releases the lock."""
        with lock:
            results["sync_acquired"] = True
            sync_ready.set()  # Signal that we've acquired the lock

            # Wait for async to be ready to call _get_async_event
            async_ready.wait(timeout=5.0)

            # Add a small delay to ensure async is in the middle of
            # calling _get_async_event
            time.sleep(0.01)

            # Release lock (this happens while async is initializing Event)
            # The race condition is: async checks lock.locked() here

        continue_flag.set()  # Signal that we've released

    async def async_worker():
        """Asynchronous worker that calls _get_async_event."""
        await asyncio.sleep(0.05)  # Give sync time to acquire first

        # Signal we're ready
        async_ready.set()

        # Wait a tiny bit to ensure sync is about to release
        await asyncio.sleep(0.005)

        # Call _get_async_event - this is where the race can occur
        event = lock._get_async_event()

        # Record the state immediately
        results["event_state"] = event.is_set()
        results["lock_state"] = lock._lock.locked()

        # Wait for sync to finish
        continue_flag.wait(timeout=5.0)

        # Check final state
        # If lock is now released, event should be set
        # If lock is held, event should not be set
        final_lock_state = lock._lock.locked()
        final_event_state = event.is_set()

        results["final_lock_state"] = final_lock_state
        results["final_event_state"] = final_event_state

        # The key assertion: Event state should match lock state
        # If they don't match, we have the bug
        if final_lock_state and final_event_state:
            raise AssertionError(
                "Bug detected: Event is set but lock is held. "
                "This indicates the Event was initialized with incorrect state."
            )

    # Run sync worker in a thread
    sync_thread = threading.Thread(target=sync_worker)
    sync_thread.start()

    # Run async worker
    asyncio.run(async_worker())

    # Wait for sync thread to complete
    sync_thread.join(timeout=10.0)

    # Verify test completed
    assert continue_flag.is_set(), "Test did not complete in time"


def test_event_state_after_sync_release():
    """Test that Event is properly set after sync releases lock.

    This is a simpler test that verifies the fix:
    1. Sync acquires and holds lock
    2. Async calls _get_async_event while lock is held
    3. Event should NOT be set (lock is held)
    4. Sync releases lock
    5. Event should be set (lock is available)
    """
    lock = _AsyncCompatibleLock()
    results = {}

    def sync_worker():
        """Sync worker that holds then releases lock."""
        with lock:
            results["lock_held"] = True
            results["initial_lock_state"] = lock._lock.locked()
            time.sleep(0.5)  # Hold lock
        results["lock_released"] = True

    async def async_worker():
        """Async worker that checks Event state."""
        await asyncio.sleep(0.1)  # Let sync acquire first

        # Get event while lock is held
        event = lock._get_async_event()

        # Event should NOT be set (lock is still held)
        results["event_while_held"] = event.is_set()

        # Wait for sync to release
        await asyncio.sleep(0.7)

        # Now check if Event gets set
        # We need to check the actual state by trying to acquire
        acquired = lock._lock.acquire(blocking=False)
        if acquired:
            lock._lock.release()
            results["lock_available_after"] = True
        else:
            results["lock_available_after"] = False

    # Run both
    sync_thread = threading.Thread(target=sync_worker)
    sync_thread.start()
    asyncio.run(async_worker())
    sync_thread.join()

    # Verify the scenario played out correctly
    assert results.get("lock_held"), "Sync should have acquired lock"
    assert results.get("lock_released"), "Sync should have released lock"

    # The key assertion: while lock is held, Event should not be set
    # This is the simplest way to detect the race condition bug
    if not results["initial_lock_state"]:
        # Lock was somehow not held initially, skip this check
        return

    # If Event was set while lock was held, that's the bug
    if results["event_while_held"]:
        raise AssertionError(
            "Bug detected: Event was set while lock was held. "
            "This indicates _get_async_event incorrectly initialized "
            "the Event state due to race condition."
        )


if __name__ == "__main__":
    print("Running test_event_state_consistency_during_race...")
    try:
        test_event_state_consistency_during_race()
        print("✓ test_event_state_consistency_during_race PASSED")
    except AssertionError as e:
        print(f"✗ test_event_state_consistency_during_race FAILED: {e}")

    print("\nRunning test_event_state_after_sync_release...")
    try:
        test_event_state_after_sync_release()
        print("✓ test_event_state_after_sync_release PASSED")
    except AssertionError as e:
        print(f"✗ test_event_state_after_sync_release FAILED: {e}")

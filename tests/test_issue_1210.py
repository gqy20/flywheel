"""Test for Issue #1210: Verify lock state consistency after timeout in __enter__.

Issue description:
In the __enter__ method, when a TimeoutError occurs, there's a potential race condition
where the lock might be acquired after the timeout but before future.cancel() takes effect.
The finally block attempts to clean up this scenario, but we need to verify that
the lock state remains consistent after such an event.
"""
import asyncio
import threading
import time
import pytest
from src.flywheel.storage import _AsyncCompatibleLock


def test_lock_state_consistency_after_timeout():
    """Test that lock state is consistent after a timeout in __enter__.

    This test ensures that even if a timeout occurs and the lock might be
    acquired in the race window, the internal state (_locked flag) remains
    consistent with the actual lock state.
    """
    lock = _AsyncCompatibleLock()

    # Create a thread that holds the lock
    def hold_lock():
        with lock:
            time.sleep(0.5)

    holder = threading.Thread(target=hold_lock)
    holder.start()

    # Give holder time to acquire the lock
    time.sleep(0.1)

    # Try to acquire the lock - will timeout
    timeout_occurred = False
    try:
        with lock:
            pass  # Should not reach here
    except TimeoutError:
        timeout_occurred = True

    assert timeout_occurred, "Timeout should have occurred"

    # Wait for holder to release
    holder.join()

    # After timeout, verify lock is in consistent state
    # The key assertion: _locked should be False since we're not in context manager
    assert not lock._locked, "_locked flag should be False after timeout exception"

    # The actual asyncio lock should also not be locked
    assert not lock._lock.locked(), "Actual lock should not be locked after timeout"

    # Should be able to use the lock normally
    with lock:
        # If we get here, lock is working correctly
        assert lock._locked, "_locked should be True inside context manager"

    # After exiting, _locked should be False again
    assert not lock._locked, "_locked should be False after exiting context"


def test_multiple_timeout_attempts():
    """Test that multiple timeout attempts don't leave lock in bad state.

    This tests that even after multiple timeout scenarios, the lock
    remains usable and consistent.
    """
    lock = _AsyncCompatibleLock()

    for i in range(3):
        # Create a thread that holds the lock
        def hold_lock():
            with lock:
                time.sleep(0.5)

        holder = threading.Thread(target=hold_lock)
        holder.start()
        time.sleep(0.1)

        # Try to acquire - will timeout
        with pytest.raises(TimeoutError):
            with lock:
                pass

        holder.join()

        # Verify state is still consistent
        assert not lock._locked, f"_locked should be False after iteration {i}"
        assert not lock._lock.locked(), f"Lock should not be locked after iteration {i}"

    # Final check - lock should still work
    with lock:
        assert lock._locked


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

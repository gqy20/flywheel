#!/usr/bin/env python3
"""Simple test script to verify Issue #1573 fix."""

import asyncio
import threading
import time
from flywheel.storage import _AsyncCompatibleLock, StorageTimeoutError


async def test_timeout_range():
    """Test that __aenter__ respects timeout_range parameter."""
    print("Testing timeout_range...")

    # Create a lock with a timeout range
    lock = _AsyncCompatibleLock(
        lock_timeout=1.0,
        timeout_range=(0.1, 0.3)
    )

    # Hold the lock in a separate thread
    lock_held = threading.Event()
    release_lock = threading.Event()

    def hold_lock_sync():
        with lock:
            lock_held.set()
            release_lock.wait(timeout=5)

    # Start thread that holds the lock
    holder_thread = threading.Thread(target=hold_lock_sync)
    holder_thread.start()
    lock_held.wait(timeout=1)

    # Try to acquire from async context
    start_time = time.time()
    exception_caught = None

    try:
        async with lock:
            pass
    except StorageTimeoutError as e:
        exception_caught = "StorageTimeoutError"
        acquisition_time = time.time() - start_time
        print(f"✓ StorageTimeoutError raised after {acquisition_time:.3f}s")
    except Exception as e:
        exception_caught = type(e).__name__
        acquisition_time = time.time() - start_time
        print(f"✗ Unexpected exception {exception_caught}: {e}")
    finally:
        release_lock.set()
        holder_thread.join(timeout=2)

    # Verify results
    assert exception_caught == "StorageTimeoutError", f"Expected StorageTimeoutError but got {exception_caught}"
    assert 0.08 <= acquisition_time <= 0.5, f"Timeout {acquisition_time:.3f}s not in expected range [0.1, 0.3]"

    print(f"✓ timeout_range test PASSED (timeout was {acquisition_time:.3f}s)")
    return True


async def test_backoff_strategy():
    """Test that __aenter__ uses custom backoff_strategy."""
    print("\nTesting backoff_strategy...")

    backoff_calls = []

    def custom_backoff(attempt: int) -> float:
        delay = 0.05
        backoff_calls.append((attempt, delay))
        return delay

    # Create a lock with custom backoff strategy
    lock = _AsyncCompatibleLock(
        lock_timeout=0.1,
        backoff_strategy=custom_backoff
    )

    # Hold the lock
    lock_held = threading.Event()
    release_lock = threading.Event()

    def hold_lock_sync():
        with lock:
            lock_held.set()
            release_lock.wait(timeout=5)

    holder_thread = threading.Thread(target=hold_lock_sync)
    holder_thread.start()
    lock_held.wait(timeout=1)

    # Try to acquire
    start_time = time.time()
    exception_caught = None

    try:
        async with lock:
            pass
    except StorageTimeoutError as e:
        exception_caught = "StorageTimeoutError"
        print(f"✓ StorageTimeoutError raised after {time.time() - start_time:.3f}s")
    except Exception as e:
        exception_caught = type(e).__name__
        print(f"✗ Unexpected exception {exception_caught}: {e}")
    finally:
        release_lock.set()
        holder_thread.join(timeout=2)

    # Verify
    assert exception_caught == "StorageTimeoutError"
    assert len(backoff_calls) > 0, "Custom backoff_strategy was not called"

    print(f"✓ backoff_strategy test PASSED (called {len(backoff_calls)} times)")
    return True


async def main():
    print("=" * 80)
    print("Testing Issue #1573 fix")
    print("=" * 80)

    try:
        await test_timeout_range()
        await test_backoff_strategy()

        print("\n" + "=" * 80)
        print("✅ All tests PASSED!")
        print("=" * 80)
        return 0
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

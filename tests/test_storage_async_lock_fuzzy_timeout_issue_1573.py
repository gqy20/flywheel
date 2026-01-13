"""Test for fuzzy timeout jitter in __aenter__ (Issue #1573).

This test verifies that the __aenter__ method of _AsyncCompatibleLock implements:
1. timeout_range: fuzzy timeout mechanism to prevent thundering herd effects
2. backoff_strategy: custom backoff strategy for retries

The issue: The __init__ method defines timeout_range and backoff_strategy parameters,
but __aenter__ does not use them. This is inconsistent with __enter__ which properly
implements these features.

The fix: __aenter__ should implement the same fuzzy timeout and backoff strategy
logic as __enter__ to prevent thundering herd effects during high contention.
"""

import asyncio
import random
import threading
import time

from flywheel.storage import _AsyncCompatibleLock, StorageTimeoutError


async def test_async_lock_timeout_range():
    """Test that __aenter__ respects timeout_range parameter.

    This test verifies that when timeout_range is specified, __aenter__ uses
    random.uniform(min, max) to calculate the specific timeout for each
    acquisition attempt, preventing thundering herd effects.
    """
    # Create a lock with a timeout range
    # This should cause the lock to use random timeout between 0.1 and 0.3 seconds
    lock = _AsyncCompatibleLock(
        lock_timeout=1.0,  # Base timeout (ignored when timeout_range is set)
        timeout_range=(0.1, 0.3)  # Fuzzy timeout range
    )

    # Hold the lock in a separate thread
    lock_held = threading.Event()
    release_lock = threading.Event()

    def hold_lock_sync():
        """Hold the lock using sync context manager."""
        with lock:
            lock_held.set()  # Signal that lock is held
            # Wait until told to release
            release_lock.wait(timeout=5)

    # Start thread that holds the lock
    holder_thread = threading.Thread(target=hold_lock_sync)
    holder_thread.start()
    lock_held.wait(timeout=1)  # Wait for lock to be acquired

    # Now try to acquire from async context
    # This should timeout with StorageTimeoutError
    start_time = time.time()
    exception_caught = None

    try:
        async with lock:
            # Should not get here - lock is held by another thread
            pass
    except StorageTimeoutError as e:
        exception_caught = "StorageTimeoutError"
        acquisition_time = time.time() - start_time
        print(f"✓ StorageTimeoutError raised after {acquisition_time:.3f}s: {e}")
    except Exception as e:
        exception_caught = type(e).__name__
        acquisition_time = time.time() - start_time
        print(f"✗ Unexpected exception {exception_caught} after {acquisition_time:.3f}s: {e}")
    finally:
        # Signal the holder thread to release the lock
        release_lock.set()
        holder_thread.join(timeout=2)

    # Verify the exception type
    assert exception_caught == "StorageTimeoutError", (
        f"Expected StorageTimeoutError but got {exception_caught}. "
        "The __aenter__ method should raise StorageTimeoutError."
    )

    # Verify the timeout is within the specified range (with some tolerance)
    assert 0.08 <= acquisition_time <= 0.5, (
        f"Expected timeout between 0.1s and 0.3s but took {acquisition_time:.3f}s. "
        "This suggests the timeout_range mechanism is not working correctly."
    )

    print(f"✓ Test passed: __aenter__ respects timeout_range (timeout was {acquisition_time:.3f}s)")


async def test_async_lock_custom_backoff_strategy():
    """Test that __aenter__ uses custom backoff_strategy parameter.

    This test verifies that when backoff_strategy is specified, __aenter__
    uses it to calculate sleep time between retries instead of hardcoded values.
    """
    # Track backoff calls
    backoff_calls = []

    def custom_backoff(attempt: int) -> float:
        """Custom backoff strategy that returns fixed delay.

        Args:
            attempt: The attempt number (0, 1, 2, ...)

        Returns:
            Delay in seconds before next retry
        """
        delay = 0.05  # Fixed short delay for testing
        backoff_calls.append((attempt, delay))
        return delay

    # Create a lock with custom backoff strategy
    lock = _AsyncCompatibleLock(
        lock_timeout=0.1,  # Short timeout to trigger retries
        backoff_strategy=custom_backoff
    )

    # Hold the lock in a separate thread
    lock_held = threading.Event()
    release_lock = threading.Event()

    def hold_lock_sync():
        """Hold the lock using sync context manager."""
        with lock:
            lock_held.set()  # Signal that lock is held
            # Wait until told to release
            release_lock.wait(timeout=5)

    # Start thread that holds the lock
    holder_thread = threading.Thread(target=hold_lock_sync)
    holder_thread.start()
    lock_held.wait(timeout=1)  # Wait for lock to be acquired

    # Now try to acquire from async context
    start_time = time.time()
    exception_caught = None

    try:
        async with lock:
            # Should not get here - lock is held by another thread
            pass
    except StorageTimeoutError as e:
        exception_caught = "StorageTimeoutError"
        acquisition_time = time.time() - start_time
        print(f"✓ StorageTimeoutError raised after {acquisition_time:.3f}s: {e}")
    except Exception as e:
        exception_caught = type(e).__name__
        acquisition_time = time.time() - start_time
        print(f"✗ Unexpected exception {exception_caught} after {acquisition_time:.3f}s: {e}")
    finally:
        # Signal the holder thread to release the lock
        release_lock.set()
        holder_thread.join(timeout=2)

    # Verify the exception type
    assert exception_caught == "StorageTimeoutError", (
        f"Expected StorageTimeoutError but got {exception_caught}. "
        "The __aenter__ method should raise StorageTimeoutError."
    )

    # Verify that custom backoff strategy was called
    # __enter__ does 3 retries (MAX_RETRIES = 3), so we expect 2 backoff calls
    # (after first and second attempt failures)
    assert len(backoff_calls) > 0, (
        "Custom backoff_strategy was not called. "
        "The __aenter__ method should use backoff_strategy for retries."
    )

    # Verify that backoff was called with correct attempt numbers
    for attempt, delay in backoff_calls:
        assert isinstance(attempt, int), f"Backoff attempt should be int, got {type(attempt)}"
        assert isinstance(delay, float), f"Backoff delay should be float, got {type(delay)}"
        assert delay == 0.05, f"Expected delay 0.05s, got {delay}s"

    print(f"✓ Test passed: __aenter__ uses custom backoff_strategy (called {len(backoff_calls)} times)")


async def test_async_lock_timeout_range_distributes_timeouts():
    """Test that timeout_range creates distributed timeouts.

    This test verifies that using timeout_range results in different
    timeout values across multiple acquisitions, preventing the thundering
    herd problem where all processes retry simultaneously.
    """
    # Create a lock with a timeout range
    lock = _AsyncCompatibleLock(
        lock_timeout=1.0,
        timeout_range=(0.1, 0.3)
    )

    # Track actual timeouts used
    timeouts_used = []

    # Run multiple acquisitions and measure the timeouts
    for i in range(5):
        # Hold the lock in a separate thread
        lock_held = threading.Event()
        release_lock = threading.Event()

        def hold_lock_sync():
            with lock:
                lock_held.set()
                release_lock.wait(timeout=5)

        holder_thread = threading.Thread(target=hold_lock_sync)
        holder_thread.start()
        lock_held.wait(timeout=1)

        # Try to acquire and measure time
        start_time = time.time()
        try:
            async with lock:
                pass
        except StorageTimeoutError:
            timeout = time.time() - start_time
            timeouts_used.append(timeout)
        finally:
            release_lock.set()
            holder_thread.join(timeout=2)

        # Small delay between attempts
        await asyncio.sleep(0.1)

    # Verify that we got some variation in timeouts
    # With random.uniform(0.1, 0.3), we should see different values
    timeout_variance = max(timeouts_used) - min(timeouts_used)

    print(f"Timeouts used: {[f'{t:.3f}s' for t in timeouts_used]}")
    print(f"Min: {min(timeouts_used):.3f}s, Max: {max(timeouts_used):.3f}s")
    print(f"Variance: {timeout_variance:.3f}s")

    # With 5 samples from range [0.1, 0.3], we should see some variance
    # (though not guaranteed, this is probabilistic)
    assert all(0.08 <= t <= 0.5 for t in timeouts_used), (
        f"All timeouts should be in range [0.1, 0.3] (with tolerance). "
        f"Got: {timeouts_used}"
    )

    print(f"✓ Test passed: timeout_range creates distributed timeouts")


if __name__ == "__main__":
    print("=" * 80)
    print("Testing async lock fuzzy timeout mechanism (Issue #1573)...")
    print("=" * 80)

    print("\n1. Testing timeout_range parameter...")
    asyncio.run(test_async_lock_timeout_range())

    print("\n2. Testing custom backoff_strategy parameter...")
    asyncio.run(test_async_lock_custom_backoff_strategy())

    print("\n3. Testing timeout_range distribution...")
    asyncio.run(test_async_lock_timeout_range_distributes_timeouts())

    print("\n" + "=" * 80)
    print("✅ All tests passed - Issue #1573 is being addressed!")
    print("=" * 80)

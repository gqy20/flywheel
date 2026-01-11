"""Test for StorageTimeoutError in __enter__ (Issue #1402).

This test verifies that the __enter__ method of _AsyncCompatibleLock raises
StorageTimeoutError (not just TimeoutError) when the lock acquisition times out.

The issue: The __enter__ method uses acquire(timeout=X) to prevent indefinite
blocking, but it raises TimeoutError instead of StorageTimeoutError. This is
inconsistent with async contexts which properly raise StorageTimeoutError.

The fix: The __enter__ method should catch TimeoutError from acquire(timeout=X)
and raise StorageTimeoutError instead, for consistency with the async implementation.
"""

import asyncio
import threading
import time

from flywheel.storage import _AsyncCompatibleLock, StorageTimeoutError


def test_lock_enter_raises_storage_timeout_error():
    """Test that __enter__ raises StorageTimeoutError on timeout.

    This test verifies that when __enter__ cannot acquire the lock within
    the timeout period, it raises StorageTimeoutError (not TimeoutError).
    This ensures consistency with async contexts which raise StorageTimeoutError.
    """
    # Create a lock with a short timeout for faster testing
    lock = _AsyncCompatibleLock(lock_timeout=0.1)

    # Hold the lock in a separate thread
    lock_held = [True]

    def hold_lock():
        """Hold the lock in a thread."""
        with lock:
            # Hold the lock until told to release
            while lock_held[0]:
                time.sleep(0.01)

    # Start thread that holds the lock
    holder_thread = threading.Thread(target=hold_lock)
    holder_thread.start()

    # Give it time to acquire the lock
    time.sleep(0.05)

    # Now try to acquire from another thread
    # This should timeout and raise StorageTimeoutError
    start_time = time.time()
    exception_caught = None

    try:
        with lock:
            # Should not get here - lock is held by another thread
            pass
    except StorageTimeoutError as e:
        # This is the expected behavior
        exception_caught = "StorageTimeoutError"
        acquisition_time = time.time() - start_time
        print(f"✓ StorageTimeoutError raised after {acquisition_time:.3f}s: {e}")
    except TimeoutError as e:
        # This is the current (incorrect) behavior
        exception_caught = "TimeoutError"
        acquisition_time = time.time() - start_time
        print(f"✗ TimeoutError raised instead of StorageTimeoutError after {acquisition_time:.3f}s: {e}")
    except Exception as e:
        exception_caught = type(e).__name__
        acquisition_time = time.time() - start_time
        print(f"✗ Unexpected exception {exception_caught} after {acquisition_time:.3f}s: {e}")
    finally:
        # Signal the holder thread to release the lock
        lock_held[0] = False
        holder_thread.join(timeout=2)

    # Verify the exception type
    assert exception_caught == "StorageTimeoutError", (
        f"Expected StorageTimeoutError but got {exception_caught}. "
        "The __enter__ method should raise StorageTimeoutError for consistency "
        "with async contexts."
    )

    # Verify the timeout was approximately the configured timeout
    assert 0.08 <= acquisition_time <= 0.3, (
        f"Expected timeout around 0.1s but took {acquisition_time:.3f}s. "
        "This suggests the timeout mechanism is not working correctly."
    )

    print("✓ Test passed: __enter__ raises StorageTimeoutError on timeout")


def test_lock_enter_custom_timeout():
    """Test that __enter__ respects custom lock_timeout parameter.

    This test verifies that the lock_timeout parameter passed to __init__
    is correctly used in __enter__ when acquiring the lock.
    """
    # Test with various timeout values
    for timeout_value in [0.05, 0.1, 0.2]:
        lock = _AsyncCompatibleLock(lock_timeout=timeout_value)

        # Hold the lock
        lock_held = [True]

        def hold_lock():
            with lock:
                while lock_held[0]:
                    time.sleep(0.01)

        holder_thread = threading.Thread(target=hold_lock)
        holder_thread.start()
        time.sleep(0.02)

        # Try to acquire - should timeout with StorageTimeoutError
        start_time = time.time()
        exception_caught = None

        try:
            with lock:
                pass
        except StorageTimeoutError:
            exception_caught = "StorageTimeoutError"
            acquisition_time = time.time() - start_time
        except TimeoutError:
            exception_caught = "TimeoutError"
            acquisition_time = time.time() - start_time
        except Exception:
            exception_caught = "Other"
            acquisition_time = time.time() - start_time
        finally:
            lock_held[0] = False
            holder_thread.join(timeout=2)

        # Verify StorageTimeoutError was raised
        assert exception_caught == "StorageTimeoutError", (
            f"For timeout={timeout_value}s: Expected StorageTimeoutError but got {exception_caught}"
        )

        # Verify timing is approximately correct (within tolerance)
        assert timeout_value * 0.8 <= acquisition_time <= timeout_value * 1.5, (
            f"For timeout={timeout_value}s: Expected timeout around {timeout_value}s "
            f"but took {acquisition_time:.3f}s"
        )

        print(f"✓ Custom timeout {timeout_value}s works correctly")


if __name__ == "__main__":
    print("Testing lock __enter__ raises StorageTimeoutError...")
    test_lock_enter_raises_storage_timeout_error()

    print("\nTesting custom lock_timeout parameter...")
    test_lock_enter_custom_timeout()

    print("\n✅ All tests passed - Issue #1402 is being addressed!")

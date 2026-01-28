"""Test timeout override context manager for locks (Issue #1463).

This test verifies that _AsyncCompatibleLock supports a nested context manager
that temporarily overrides the lock timeout for a specific block, then restores
the original value.
"""

import pytest
import threading
import time

from flywheel.storage import _AsyncCompatibleLock


class TestLockTimeoutOverride:
    """Test timeout override context manager for locks."""

    def test_timeout_context_manager_exists(self):
        """Test that the timeout context manager method exists."""
        lock = _AsyncCompatibleLock(lock_timeout=10.0)

        # The lock should have a timeout method that returns a context manager
        assert hasattr(lock, 'timeout'), "Lock should have a timeout method"
        assert callable(lock.timeout), "timeout attribute should be callable"

    def test_timeout_context_manager_temporarily_overrides_timeout(self):
        """Test that timeout context manager temporarily overrides the lock timeout."""
        lock = _AsyncCompatibleLock(lock_timeout=10.0)

        # Verify initial timeout
        assert lock._lock_timeout == 10.0

        # Use the context manager to override timeout
        with lock.timeout(new_timeout=5.0):
            # Inside the context, timeout should be overridden
            assert lock._lock_timeout == 5.0

        # Outside the context, timeout should be restored
        assert lock._lock_timeout == 10.0

    def test_timeout_context_manager_with_different_values(self):
        """Test timeout context manager with various timeout values."""
        lock = _AsyncCompatibleLock(lock_timeout=10.0)

        # Test with a shorter timeout
        with lock.timeout(new_timeout=1.0):
            assert lock._lock_timeout == 1.0

        # Verify restoration
        assert lock._lock_timeout == 10.0

        # Test with a longer timeout
        with lock.timeout(new_timeout=30.0):
            assert lock._lock_timeout == 30.0

        # Verify restoration
        assert lock._lock_timeout == 10.0

    def test_timeout_context_manager_nested(self):
        """Test nested timeout context managers."""
        lock = _AsyncCompatibleLock(lock_timeout=10.0)

        with lock.timeout(new_timeout=5.0):
            assert lock._lock_timeout == 5.0

            # Nested context manager
            with lock.timeout(new_timeout=2.0):
                assert lock._lock_timeout == 2.0

            # Back to first override
            assert lock._lock_timeout == 5.0

        # Back to original
        assert lock._lock_timeout == 10.0

    def test_timeout_context_manager_affects_lock_acquisition(self):
        """Test that the timeout override actually affects lock acquisition."""
        lock = _AsyncCompatibleLock(lock_timeout=10.0)
        acquired = []

        def hold_lock_briefly():
            """Hold the lock for a short time."""
            with lock:
                time.sleep(0.2)
                acquired.append("holder")

        # Start a thread that will hold the lock
        holder = threading.Thread(target=hold_lock_briefly)
        holder.start()

        # Give the holder time to acquire the lock
        time.sleep(0.05)

        # Try to acquire with a very short timeout
        # This should fail quickly
        start_time = time.time()
        with lock.timeout(new_timeout=0.1):
            try:
                with lock:
                    acquired.append("acquirer")
            except Exception:
                # Expected to timeout
                elapsed = time.time() - start_time
                # Should timeout quickly due to the overridden timeout
                assert elapsed < 0.5, f"Expected quick timeout but took {elapsed:.2f}s"

        holder.join()

    def test_timeout_context_manager_exception_safety(self):
        """Test that timeout is restored even if an exception occurs."""
        lock = _AsyncCompatibleLock(lock_timeout=10.0)

        try:
            with lock.timeout(new_timeout=5.0):
                assert lock._lock_timeout == 5.0
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Timeout should be restored after exception
        assert lock._lock_timeout == 10.0

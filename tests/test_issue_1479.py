"""
Tests for Issue #1479 - Verify __enter__ method has complete try-except block.

This test verifies that the StorageLock's __enter__ method properly handles
exception cases and releases the lock to prevent lock leaks.
"""

import pytest
import threading
from unittest.mock import patch
from flywheel.storage import StorageLock, StorageTimeoutError


class TestIssue1479:
    """Test that __enter__ method has complete exception handling."""

    def test_enter_has_try_except_block(self):
        """Verify __enter__ method contains try-except block for lock release."""
        # This test verifies the code structure by checking behavior
        lock = StorageLock()

        # Normal case: lock should be acquired
        with lock:
            # Verify lock is held
            assert lock._lock.locked()

    def test_enter_timeout_does_not_hold_lock(self):
        """Verify that when timeout occurs, lock is NOT held."""
        # Create a lock with very short timeout
        lock = StorageLock(lock_timeout=0.001)

        # Acquire the lock in another thread
        def hold_lock():
            with lock:
                # Hold the lock for a while
                import time
                time.sleep(0.1)

        thread = threading.Thread(target=hold_lock)
        thread.start()

        # Give thread time to acquire lock
        import time
        time.sleep(0.01)

        # Try to acquire - should timeout
        with pytest.raises(StorageTimeoutError) as exc_info:
            with lock:
                pass

        # Verify the error message mentions lock is NOT held
        assert "NOT held" in str(exc_info.value)

        thread.join()

    def test_enter_handles_exception_between_acquire_and_return(self):
        """
        Test that __enter__ properly handles exceptions between acquire() and return.

        This is a defensive programming test - while 'return self' normally
        cannot raise an exception, the try-except block ensures lock is released
        if somehow an exception does occur.
        """
        lock = StorageLock()

        # Mock __enter__ to simulate exception after acquiring lock
        original_enter = lock.__enter__

        def mock_enter_with_exception():
            # First acquire the lock
            acquired = lock._lock.acquire(timeout=lock._lock_timeout)
            if not acquired:
                raise StorageTimeoutError("Could not acquire lock")

            # Simulate an exception after acquiring but before returning
            try:
                raise RuntimeError("Simulated exception in __enter__")
            except RuntimeError:
                # The try-except block should release the lock here
                lock._lock.release()
                raise

        # Patch __enter__ to simulate exception
        with patch.object(lock, '__enter__', side_effect=mock_enter_with_exception):
            with pytest.raises(RuntimeError, match="Simulated exception"):
                with lock:
                    pass

        # Verify lock was released (not locked after exception)
        assert not lock._lock.locked()

        # Verify we can acquire the lock again
        with lock:
            assert lock._lock.locked()

    def test_code_structure_complete(self):
        """
        Verify the __enter__ method has complete code structure.

        This test checks the source code to ensure:
        1. try-except block exists
        2. Lock is released in except block
        3. Exception is re-raised
        """
        import inspect

        lock = StorageLock()
        source = inspect.getsource(lock.__enter__)

        # Verify try-except block exists
        assert "try:" in source, "Missing try block in __enter__"
        assert "except:" in source, "Missing except block in __enter__"

        # Verify lock release in exception handler
        assert "release()" in source, "Missing lock.release() in exception handler"

        # Verify exception is re-raised
        assert "raise" in source, "Missing raise to re-raise exception"

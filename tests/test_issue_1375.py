"""Test for issue #1375 - Verify lock context manager has complete implementation.

Issue #1375 reports that code truncation caused syntax errors in the lock implementation.
This test verifies that:
1. The __enter__ method is complete and properly implemented
2. The __exit__ method is complete and properly implemented
3. Both methods work correctly as a context manager
4. No syntax errors exist from code truncation
"""

import threading
import time
import pytest
from src.flywheel.storage import _AsyncCompatibleLock


class TestIssue1375:
    """Test that lock context manager is complete and functional."""

    def test_lock_context_manager_basic(self):
        """Test basic sync context manager functionality."""
        lock = _AsyncCompatibleLock()

        # Test that we can use the lock as a context manager
        with lock:
            # Lock should be held inside the context
            assert lock._lock.locked()

        # Lock should be released after exiting context
        assert not lock._lock.locked()

    def test_lock_context_manager_exception_handling(self):
        """Test that lock is properly released even when exception occurs."""
        lock = _AsyncCompatibleLock()

        with pytest.raises(ValueError):
            with lock:
                assert lock._lock.locked()
                raise ValueError("Test exception")

        # Lock should be released even after exception
        assert not lock._lock.locked()

    def test_lock_context_manager_thread_safety(self):
        """Test that lock provides proper mutual exclusion between threads."""
        lock = _AsyncCompatibleLock()
        results = []
        errors = []

        def worker(value):
            try:
                with lock:
                    # Simulate some work
                    time.sleep(0.01)
                    results.append(value)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should have completed without errors
        assert len(errors) == 0
        assert len(results) == 5

    def test_lock_acquire_and_release(self):
        """Test that lock can be acquired and released correctly."""
        lock = _AsyncCompatibleLock()

        # Initial state - lock should not be held
        assert not lock._lock.locked()

        # Acquire using context manager
        with lock:
            assert lock._lock.locked()

        # Should be released after context
        assert not lock._lock.locked()

    def test_lock_timeout(self):
        """Test that lock timeout parameter is stored correctly."""
        lock = _AsyncCompatibleLock(lock_timeout=5.0)
        assert lock._lock_timeout == 5.0

        default_lock = _AsyncCompatibleLock()
        assert default_lock._lock_timeout == 10.0

    def test_lock_is_context_manager(self):
        """Test that lock implements context manager protocol."""
        lock = _AsyncCompatibleLock()

        # Check that __enter__ and __exit__ exist and are callable
        assert hasattr(lock, '__enter__')
        assert hasattr(lock, '__exit__')
        assert callable(lock.__enter__)
        assert callable(lock.__exit__)

    def test_lock_enter_returns_self(self):
        """Test that __enter__ returns self for proper context manager protocol."""
        lock = _AsyncCompatibleLock()

        # __enter__ must return self for the context manager to work correctly
        result = lock.__enter__()
        assert result is lock, "__enter__ should return self"

        # Clean up - release the lock
        lock.__exit__(None, None, None)

    def test_lock_exit_returns_false(self):
        """Test that __exit__ returns False to propagate exceptions."""
        lock = _AsyncCompatibleLock()

        # Acquire the lock first
        lock.__enter__()

        # __exit__ should return False to propagate exceptions
        result = lock.__exit__(None, None, None)
        assert result is False, "__exit__ should return False"

"""Tests for exponential backoff in lock acquisition retries.

Issue #1498: Implement exponential backoff for lock acquisition retries.
"""

import time
import threading
from unittest.mock import patch
import pytest

from flywheel.storage import _AsyncCompatibleLock, StorageTimeoutError


class TestExponentialBackoff:
    """Test exponential backoff for lock acquisition retries."""

    def test_lock_retry_on_initial_timeout(self):
        """Test that lock acquisition retries after initial timeout with exponential backoff."""
        lock = _AsyncCompatibleLock(lock_timeout=0.01)  # Very short timeout

        # Acquire the lock in another thread to force contention
        def hold_lock():
            with lock:
                time.sleep(0.3)  # Hold long enough to trigger multiple retries

        holder_thread = threading.Thread(target=hold_lock)
        holder_thread.start()

        # Give the holder thread time to acquire the lock
        time.sleep(0.02)

        # Try to acquire - should retry with exponential backoff
        # The holder releases after 0.3s, so retry should succeed
        start = time.time()
        try:
            with lock:
                elapsed = time.time() - start
                # Should succeed after retries, taking more than initial timeout
                # but less than total retry time (3 retries with exponential backoff)
                assert elapsed > 0.01, "Should have retried after initial timeout"
                assert elapsed < 0.5, f"Should have acquired lock within retry period, took {elapsed}s"
        except StorageTimeoutError:
            pytest.fail("Should have acquired lock after retry, but got timeout")
        finally:
            holder_thread.join()

    def test_lock_fails_after_max_retries(self):
        """Test that lock acquisition fails after max retries."""
        lock = _AsyncCompatibleLock(lock_timeout=0.01)  # Very short timeout

        # Acquire the lock in another thread and hold it longer than retry period
        def hold_lock():
            with lock:
                time.sleep(1.0)  # Hold longer than total retry time

        holder_thread = threading.Thread(target=hold_lock)
        holder_thread.start()

        # Give the holder thread time to acquire the lock
        time.sleep(0.02)

        # Try to acquire - should exhaust retries and fail
        start = time.time()
        with pytest.raises(StorageTimeoutError) as exc_info:
            with lock:
                pass

        elapsed = time.time() - start
        holder_thread.join()

        # Should have taken time for all retries
        assert elapsed > 0.05, "Should have attempted multiple retries"
        assert "Could not acquire lock" in str(exc_info.value)

    def test_lock_immediate_acquire_when_free(self):
        """Test that lock acquisition is immediate when lock is free."""
        lock = _AsyncCompatibleLock(lock_timeout=0.01)

        start = time.time()
        with lock:
            pass
        elapsed = time.time() - start

        # Should acquire immediately without retries
        assert elapsed < 0.05, "Should acquire immediately when lock is free"

    @patch('random.uniform')
    def test_exponential_backoff_timing(self, mock_uniform):
        """Test that retry delays follow exponential backoff pattern."""
        # Mock random.uniform to return predictable values
        mock_uniform.side_effect = [0.05, 0.1, 0.15]

        lock = _AsyncCompatibleLock(lock_timeout=0.01)

        # Acquire the lock in another thread
        def hold_lock():
            with lock:
                time.sleep(0.3)

        holder_thread = threading.Thread(target=hold_lock)
        holder_thread.start()
        time.sleep(0.02)

        start = time.time()
        try:
            with lock:
                pass
        except StorageTimeoutError:
            # Expected - we're testing the retry pattern
            pass
        finally:
            holder_thread.join()

        # The mock should have been called for retries
        # with exponential backoff (increasing delays)
        assert mock_uniform.call_count >= 1, "Should have used randomized backoff"

        # Verify that the intervals increase (exponential backoff)
        # Each call should have an increasing upper bound
        calls = mock_uniform.call_args_list
        if len(calls) >= 2:
            # Second retry should have longer max delay than first
            first_max = calls[0][0][1]  # Second arg is max
            second_max = calls[1][0][1]
            assert second_max > first_max, "Should use exponential backoff with increasing delays"

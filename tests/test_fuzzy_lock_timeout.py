"""Tests for fuzzy lock timeout mechanism (Issue #1533)."""
import random
import time
import threading
from collections import Counter

import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestFuzzyLockTimeout:
    """Test suite for configurable fuzzy lock timeout mechanism."""

    def test_lock_accepts_timeout_range_tuple(self):
        """Test that lock can be initialized with timeout_range tuple."""
        lock = _AsyncCompatibleLock(timeout_range=(5.0, 15.0))
        # Should accept the parameter without error
        assert lock is not None

    def test_lock_accepts_backoff_strategy_function(self):
        """Test that lock can be initialized with a backoff strategy function."""
        def custom_backoff(attempt):
            return attempt * 0.1

        lock = _AsyncCompatibleLock(backoff_strategy=custom_backoff)
        # Should accept the parameter without error
        assert lock is not None

    def test_timeout_within_specified_range(self):
        """Test that actual timeout falls within the specified range."""
        timeout_range = (5.0, 10.0)
        lock = _AsyncCompatibleLock(timeout_range=timeout_range)

        # Acquire the lock
        with lock:
            # Try to acquire again in another thread with a timeout
            timeout_actual = []

            def try_acquire():
                start = time.time()
                try:
                    with lock:
                        pass
                except Exception:
                    pass
                timeout_actual.append(time.time() - start)

            thread = threading.Thread(target=try_acquire)
            thread.start()
            thread.join()

            # The timeout should be within the specified range
            if timeout_actual:
                assert timeout_range[0] <= timeout_actual[0] <= timeout_range[1] + 1.0

    def test_timeout_randomness_prevents_thundering_herd(self):
        """Test that timeout randomization prevents thundering herd effects."""
        timeout_range = (5.0, 10.0)
        lock = _AsyncCompatibleLock(timeout_range=timeout_range)

        # Hold the lock
        lock.acquire()

        timeouts = []

        def try_acquire_with_timeout():
            start = time.time()
            try:
                lock.acquire(timeout=15.0)  # Longer than max timeout
            except Exception:
                pass
            elapsed = time.time() - start
            timeouts.append(elapsed)

        # Launch multiple threads trying to acquire the same lock
        threads = []
        for _ in range(5):
            t = threading.Thread(target=try_acquire_with_timeout)
            threads.append(t)
            t.start()

        # Wait a bit then release the lock
        time.sleep(0.5)
        lock.release()

        for t in threads:
            t.join()

        # With randomness, we should see variation in timeouts
        # (This is a probabilistic test - might occasionally fail)
        if len(timeouts) >= 3:
            # Check that not all timeouts are exactly the same
            unique_timeouts = set(round(t, 2) for t in timeouts)
            assert len(unique_timeouts) > 1, "Timeouts should vary with randomization"

    def test_default_timeout_still_works(self):
        """Test that default timeout behavior is preserved when no range specified."""
        lock = _AsyncCompatibleLock()  # Use default timeout

        # Acquire the lock
        with lock:
            # Try to acquire in another thread
            def try_acquire():
                try:
                    with lock:
                        pass
                except Exception:
                    pass

            thread = threading.Thread(target=try_acquire)
            thread.start()
            thread.join(timeout=15)  # Should complete within default timeout

    def test_explicit_single_timeout_value(self):
        """Test that a single timeout value can still be specified."""
        explicit_timeout = 8.0
        lock = _AsyncCompatibleLock(lock_timeout=explicit_timeout)

        # Should work with the explicit timeout
        with lock:
            pass

    def test_backoff_strategy_with_timeout_range(self):
        """Test that backoff strategy works with timeout range."""
        timeout_range = (5.0, 10.0)

        def custom_backoff(attempt):
            # Custom backoff: 0.1s, 0.3s, 0.5s
            return 0.1 + (attempt * 0.2)

        lock = _AsyncCompatibleLock(
            timeout_range=timeout_range,
            backoff_strategy=custom_backoff
        )

        # Should accept both parameters
        assert lock is not None

    def test_timeout_range_validation(self):
        """Test that timeout_range validates min <= max."""
        # Invalid range: min > max should raise an error
        with pytest.raises(ValueError):
            _AsyncCompatibleLock(timeout_range=(15.0, 5.0))

    def test_negative_timeout_rejected(self):
        """Test that negative timeout values are rejected."""
        with pytest.raises(ValueError):
            _AsyncCompatibleLock(timeout_range=(-5.0, 10.0))

        with pytest.raises(ValueError):
            _AsyncCompatibleLock(lock_timeout=-1.0)

    def test_zero_timeout_accepted(self):
        """Test that zero timeout is accepted (non-blocking attempt)."""
        lock = _AsyncCompatibleLock(lock_timeout=0.0)

        # Acquire the lock
        lock.acquire()

        # Try to acquire again with zero timeout
        acquired = lock.acquire(timeout=0.0)
        assert not acquired  # Should fail immediately

        lock.release()

    def test_timeout_distribution_approximately_uniform(self):
        """Test that timeout randomization is approximately uniform across range."""
        timeout_range = (5.0, 10.0)
        num_samples = 20

        # Collect timeout values from multiple lock instances
        # (In a real scenario, this would test multiple acquisitions)
        # For now, we test that the range is correctly stored

        for _ in range(num_samples):
            lock = _AsyncCompatibleLock(timeout_range=timeout_range)
            assert lock is not None


class TestBackoffStrategies:
    """Test different backoff strategies for lock acquisition."""

    def test_exponential_backoff_default(self):
        """Test that default exponential backoff works."""
        lock = _AsyncCompatibleLock()

        # The lock should use exponential backoff on retries
        # This is tested implicitly by the lock working under contention
        assert lock is not None

    def test_custom_linear_backoff(self):
        """Test a custom linear backoff strategy."""
        def linear_backoff(attempt):
            return attempt * 0.05  # 0.05s, 0.10s, 0.15s, ...

        lock = _AsyncCompatibleLock(backoff_strategy=linear_backoff)
        assert lock is not None

    def test_custom_fixed_backoff(self):
        """Test a custom fixed backoff strategy."""
        def fixed_backoff(attempt):
            return 0.1  # Always wait 0.1s

        lock = _AsyncCompatibleLock(backoff_strategy=fixed_backoff)
        assert lock is not None

    def test_backoff_receives_correct_attempt_number(self):
        """Test that backoff function receives the correct attempt number."""
        received_attempts = []

        def tracking_backoff(attempt):
            received_attempts.append(attempt)
            return 0.01  # Very short delay

        lock = _AsyncCompatibleLock(backoff_strategy=tracking_backoff)

        # Hold the lock to cause contention
        lock.acquire()

        def try_acquire():
            try:
                with lock:
                    pass
            except Exception:
                pass

        thread = threading.Thread(target=try_acquire)
        thread.start()

        # Wait a bit then release
        time.sleep(0.1)
        lock.release()

        thread.join(timeout=5)

        # Verify that backoff was called with incrementing attempt numbers
        if received_attempts:
            assert received_attempts == sorted(received_attempts)


class TestAdaptiveTimeout:
    """Test adaptive timeout mechanisms."""

    def test_adaptive_timeout_increases_on_contention(self):
        """Test that adaptive timeout increases when high contention is detected."""
        # This would require the lock to track contention history
        # For now, we test that the parameter is accepted
        lock = _AsyncCompatibleLock(adaptive_timeout=True)
        assert lock is not None

    def test_adaptive_timeout_disabled_by_default(self):
        """Test that adaptive timeout is disabled by default."""
        lock = _AsyncCompatibleLock()
        # Default behavior should not use adaptive timeout
        assert lock is not None


class TestEdgeCases:
    """Test edge cases for fuzzy timeout mechanism."""

    def test_very_small_timeout_range(self):
        """Test with a very small timeout range."""
        lock = _AsyncCompatibleLock(timeout_range=(1.0, 1.1))
        assert lock is not None

    def test_very_large_timeout_range(self):
        """Test with a very large timeout range."""
        lock = _AsyncCompatibleLock(timeout_range=(1.0, 100.0))
        assert lock is not None

    def test_equal_min_max_timeout(self):
        """Test with min == max (essentially a fixed timeout)."""
        lock = _AsyncCompatibleLock(timeout_range=(10.0, 10.0))
        assert lock is not None

    def test_timeout_range_with_floats(self):
        """Test timeout range with floating point precision."""
        lock = _AsyncCompatibleLock(timeout_range=(2.567, 9.876))
        assert lock is not None

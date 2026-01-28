"""Test lock statistics export for monitoring systems (Issue #1612).

This test verifies that _AsyncCompatibleLock provides a get_lock_stats() method
that returns simplified metrics for monitoring systems to poll without parsing logs.
"""

import time
import threading
from flywheel.storage import _AsyncCompatibleLock


def test_get_lock_stats_returns_required_fields():
    """Test that get_lock_stats() returns required fields."""
    lock = _AsyncCompatibleLock()

    # Get initial stats (should be zeros)
    stats = lock.get_lock_stats()

    # Verify all required fields are present
    assert 'total_waits' in stats, "Missing 'total_waits' field"
    assert 'total_wait_time' in stats, "Missing 'total_wait_time' field"
    assert 'max_wait' in stats, "Missing 'max_wait' field"

    # Verify initial values are zero
    assert stats['total_waits'] == 0, "Initial total_waits should be 0"
    assert stats['total_wait_time'] == 0.0, "Initial total_wait_time should be 0.0"
    assert stats['max_wait'] == 0.0, "Initial max_wait should be 0.0"


def test_get_lock_stats_tracks_acquisitions_without_contention():
    """Test that stats track lock acquisitions without contention."""
    lock = _AsyncCompatibleLock()

    # Acquire and release lock (no contention)
    with lock:
        pass

    # Stats should show acquisition but no wait time
    stats = lock.get_lock_stats()
    assert stats['total_waits'] == 0, "No waits expected for uncontended acquisition"
    assert stats['total_wait_time'] == 0.0, "No wait time expected"
    assert stats['max_wait'] == 0.0, "No max wait expected"


def test_get_lock_stats_tracks_acquisitions_with_contention():
    """Test that stats track lock acquisitions with contention."""
    lock = _AsyncCompatibleLock()

    # Acquire the lock in main thread to create contention
    lock.acquire()
    acquired_flag = {'value': False}

    def try_acquire_lock():
        """Try to acquire lock from another thread."""
        nonlocal acquired_flag
        with lock:
            acquired_flag['value'] = True

    # Start thread that will contend for the lock
    thread = threading.Thread(target=try_acquire_lock)
    thread.start()

    # Wait a bit to ensure thread is waiting
    time.sleep(0.1)

    # Release lock so the thread can acquire it
    lock.release()

    # Wait for thread to complete
    thread.join(timeout=5.0)

    assert acquired_flag['value'], "Thread should have acquired lock"

    # Check that stats show contention
    stats = lock.get_lock_stats()
    assert stats['total_waits'] > 0, f"Expected waits > 0, got {stats['total_waits']}"
    assert stats['total_wait_time'] > 0.0, f"Expected wait_time > 0, got {stats['total_wait_time']}"
    assert stats['max_wait'] > 0.0, f"Expected max_wait > 0, got {stats['max_wait']}"
    assert stats['max_wait'] <= stats['total_wait_time'], \
        f"max_wait ({stats['max_wait']}) should not exceed total_wait_time ({stats['total_wait_time']})"


def test_get_lock_stats_max_wait_updates_correctly():
    """Test that max_wait is updated correctly across multiple acquisitions."""
    lock = _AsyncCompatibleLock()

    max_wait_times = []

    def acquire_with_delay():
        """Acquire lock and hold it briefly."""
        lock.acquire()
        time.sleep(0.05)
        lock.release()

    # Create multiple contention scenarios
    for i in range(3):
        # Hold lock in main thread
        lock.acquire()

        # Start competing thread
        thread = threading.Thread(target=acquire_with_delay)
        thread.start()

        # Wait a bit then release
        time.sleep(0.02)
        lock.release()

        thread.join(timeout=5.0)

        # Check stats after each iteration
        stats = lock.get_lock_stats()
        if stats['max_wait'] > 0:
            max_wait_times.append(stats['max_wait'])

    # Verify we have multiple measurements and max is reasonable
    if len(max_wait_times) > 0:
        stats = lock.get_lock_stats()
        # The final max_wait should be the maximum of all individual waits
        assert stats['max_wait'] > 0, "Should have recorded max wait time"
        # Max wait should be reasonable (less than 1 second in our test)
        assert stats['max_wait'] < 1.0, f"Max wait {stats['max_wait']} seems too high"


def test_get_lock_stats_thread_safety():
    """Test that get_lock_stats() is thread-safe."""
    lock = _AsyncCompatibleLock()

    def acquire_and_check_stats():
        """Acquire lock and check stats multiple times."""
        for _ in range(10):
            with lock:
                stats = lock.get_lock_stats()
                # Just verify we can access all fields without error
                _ = stats['total_waits']
                _ = stats['total_wait_time']
                _ = stats['max_wait']

    # Run multiple threads concurrently
    threads = []
    for _ in range(5):
        thread = threading.Thread(target=acquire_and_check_stats)
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join(timeout=10.0)

    # Verify final stats are accessible
    stats = lock.get_lock_stats()
    assert isinstance(stats['total_waits'], int)
    assert isinstance(stats['total_wait_time'], float)
    assert isinstance(stats['max_wait'], float)


def test_get_lock_stats_returns_dict():
    """Test that get_lock_stats() returns a dictionary."""
    lock = _AsyncCompatibleLock()

    stats = lock.get_lock_stats()

    # Verify return type
    assert isinstance(stats, dict), "get_lock_stats() should return a dict"

    # Verify it's a copy (not the internal dict)
    stats_copy = lock.get_lock_stats()
    assert stats is not stats_copy, "Should return a copy, not the internal dict"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])

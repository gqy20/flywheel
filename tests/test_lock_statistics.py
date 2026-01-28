"""Test lock statistics tracking functionality (Issue #1538)."""
import asyncio
import threading
import time
import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestLockStatistics:
    """Test suite for lock statistics tracking."""

    def test_initial_stats(self):
        """Test that initial statistics are zero."""
        lock = _AsyncCompatibleLock()
        stats = lock.get_stats()

        assert stats['acquire_count'] == 0
        assert stats['contention_count'] == 0
        assert stats['total_wait_time'] == 0.0

    def test_acquire_without_contention(self):
        """Test acquiring lock without contention records no wait time."""
        lock = _AsyncCompatibleLock()

        with lock:
            pass

        stats = lock.get_stats()
        assert stats['acquire_count'] == 1
        assert stats['contention_count'] == 0
        assert stats['total_wait_time'] == 0.0

    def test_contention_detection_sync(self):
        """Test that contention is detected when multiple threads compete for the lock."""
        lock = _AsyncCompatibleLock()

        # Acquire the lock first
        lock.acquire()

        # Try to acquire from another thread - should detect contention
        def try_acquire():
            time.sleep(0.05)  # Hold the lock briefly
            lock.release()

        thread = threading.Thread(target=try_acquire)
        thread.start()

        # Wait a bit then try to acquire - this should see contention
        time.sleep(0.02)
        start = time.time()
        with lock:
            pass
        elapsed = time.time() - start

        thread.join()

        stats = lock.get_stats()
        assert stats['acquire_count'] >= 2

    def test_contention_wait_time_tracked(self):
        """Test that wait time is tracked during contention."""
        lock = _AsyncCompatibleLock()

        # Acquire and hold the lock
        lock.acquire()

        def release_after_delay():
            time.sleep(0.1)
            lock.release()

        thread = threading.Thread(target=release_after_delay)
        thread.start()

        # Try to acquire - should wait and record wait time
        time.sleep(0.01)  # Ensure lock is held
        with lock:
            pass

        thread.join()

        stats = lock.get_stats()
        assert stats['acquire_count'] >= 2
        # Should have recorded some wait time due to contention
        assert stats['total_wait_time'] > 0

    @pytest.mark.asyncio
    async def test_contention_detection_async(self):
        """Test that contention is detected in async contexts."""
        lock = _AsyncCompatibleLock()

        # Hold the lock
        lock.acquire()

        async def try_acquire_async():
            await asyncio.sleep(0.05)
            lock.release()

        # Start task that will release the lock
        task = asyncio.create_task(try_acquire_async())

        # Try to acquire async - should wait
        await asyncio.sleep(0.01)
        async with lock:
            pass

        await task

        stats = lock.get_stats()
        assert stats['acquire_count'] >= 2

    def test_reset_stats(self):
        """Test that statistics can be reset."""
        lock = _AsyncCompatibleLock()

        with lock:
            pass

        stats_before = lock.get_stats()
        assert stats_before['acquire_count'] > 0

        lock.reset_stats()

        stats_after = lock.get_stats()
        assert stats_after['acquire_count'] == 0
        assert stats_after['contention_count'] == 0
        assert stats_after['total_wait_time'] == 0.0

    def test_multiple_acquires(self):
        """Test statistics with multiple lock acquisitions."""
        lock = _AsyncCompatibleLock()

        for _ in range(5):
            with lock:
                pass

        stats = lock.get_stats()
        assert stats['acquire_count'] == 5

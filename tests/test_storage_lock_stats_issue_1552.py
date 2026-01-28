"""Test lock statistics reporting (Issue #1552)."""
import asyncio
import threading
import time
from io import StringIO

import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestLockStatsReporting:
    """Test lock statistics get_stats() and log_stats() methods."""

    def test_get_stats_returns_expected_keys(self):
        """Test that get_stats() returns all expected keys."""
        lock = _AsyncCompatibleLock()
        stats = lock.get_stats()

        # Check that all expected keys are present
        assert "acquire_count" in stats
        assert "contention_count" in stats
        assert "total_wait_time" in stats
        assert "average_wait_time" in stats
        assert "contention_rate" in stats

    def test_get_stats_initial_values(self):
        """Test that get_stats() returns zero values for new lock."""
        lock = _AsyncCompatibleLock()
        stats = lock.get_stats()

        assert stats["acquire_count"] == 0
        assert stats["contention_count"] == 0
        assert stats["total_wait_time"] == 0.0
        assert stats["average_wait_time"] == 0.0
        assert stats["contention_rate"] == 0.0

    def test_get_stats_after_acquire(self):
        """Test that get_stats() reports acquire count after using lock."""
        lock = _AsyncCompatibleLock()

        # Acquire lock once
        with lock:
            pass

        stats = lock.get_stats()
        assert stats["acquire_count"] == 1

    def test_get_stats_tracks_contention(self):
        """Test that get_stats() tracks lock contention."""
        lock = _AsyncCompatibleLock()
        acquired = []

        def worker():
            with lock:
                acquired.append(1)
                time.sleep(0.1)  # Hold lock to cause contention

        # Start first thread
        t1 = threading.Thread(target=worker)
        t1.start()

        # Wait a bit then start second thread (will cause contention)
        time.sleep(0.05)
        t2 = threading.Thread(target=worker)
        t2.start()

        t1.join()
        t2.join()

        stats = lock.get_stats()
        assert stats["acquire_count"] == 2
        # At least one acquisition should have contention
        assert stats["contention_count"] >= 1

    def test_get_stats_average_wait_time(self):
        """Test that get_stats() calculates average wait time correctly."""
        lock = _AsyncCompatibleLock()

        def blocking_acquire():
            with lock:
                time.sleep(0.05)

        # Start first thread that holds the lock
        t1 = threading.Thread(target=blocking_acquire)
        t1.start()

        # Wait a bit then acquire (will have to wait)
        time.sleep(0.01)
        start = time.time()
        with lock:
            wait_time = time.time() - start
            # We should have waited for the first thread

        t1.join()

        stats = lock.get_stats()
        assert stats["acquire_count"] >= 1
        if stats["contention_count"] > 0:
            assert stats["total_wait_time"] > 0
            assert stats["average_wait_time"] > 0

    def test_log_stats_writes_to_logger(self):
        """Test that log_stats() writes statistics to logger."""
        lock = _AsyncCompatibleLock()

        # Use the lock a few times
        for _ in range(3):
            with lock:
                pass

        # Capture log output
        import logging
        logger = logging.getLogger("flywheel.storage")
        logger.setLevel(logging.DEBUG)

        # Create a string handler to capture output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        try:
            # Log stats
            lock.log_stats()

            # Get output
            output = log_stream.getvalue()

            # Check that output contains key information
            assert "acquire_count" in output or "acquire" in output.lower()
            assert "contention" in output.lower() or "wait" in output.lower()
        finally:
            logger.removeHandler(handler)

    def test_log_stats_with_custom_message(self):
        """Test that log_stats() can include custom message."""
        lock = _AsyncCompatibleLock()

        import logging
        logger = logging.getLogger("flywheel.storage")
        logger.setLevel(logging.DEBUG)

        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        try:
            lock.log_stats(message="Custom prefix")

            output = log_stream.getvalue()
            assert "Custom prefix" in output
        finally:
            logger.removeHandler(handler)

    def test_stats_thread_safety(self):
        """Test that stats operations are thread-safe."""
        lock = _AsyncCompatibleLock()
        results = []

        def worker():
            for _ in range(10):
                with lock:
                    pass
            # Get stats while lock might be used by other threads
            stats = lock.get_stats()
            results.append(stats)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should have completed without errors
        assert len(results) == 5

        # Final stats should reflect all acquisitions
        final_stats = lock.get_stats()
        assert final_stats["acquire_count"] == 50  # 5 threads * 10 acquisitions

    def test_async_lock_stats(self):
        """Test that stats work correctly with async lock usage."""
        lock = _AsyncCompatibleLock()

        async def use_lock():
            async with lock:
                await asyncio.sleep(0.01)

        # Run async operations
        asyncio.run(use_lock())
        asyncio.run(use_lock())

        stats = lock.get_stats()
        assert stats["acquire_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

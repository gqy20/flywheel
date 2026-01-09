"""Tests for IOMetrics thread safety in _get_async_lock (Issue #1150).

This test ensures that IOMetrics._get_async_lock properly handles the case where
it might be called from different threads with different event loops.

The bug is that asyncio.Lock() is created without specifying an event loop,
which can cause RuntimeError when used in multi-threaded environments where
different threads have different event loops.
"""

import asyncio
import threading
import pytest


class TestIOMetricsThreadSafetyIssue1150:
    """Test suite for IOMetrics thread safety in _get_async_lock (Issue #1150)."""

    @pytest.mark.asyncio
    async def test_lock_created_in_correct_event_loop(self):
        """Test that asyncio.Lock is created in the calling event loop.

        The bug is that if the lock is created in one event loop but used in
        another, it will cause a RuntimeError.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()

        # Get lock in current event loop
        lock1 = metrics._get_async_lock()

        # Verify it's an asyncio.Lock
        assert isinstance(lock1, asyncio.Lock)

        # Verify we can use it
        async with lock1:
            await metrics.record_operation_async(
                "read",
                duration=0.1,
                retries=0,
                success=True
            )

        # Verify operation was recorded
        assert len(metrics.operations) == 1

    @pytest.mark.asyncio
    async def test_multiple_event_loops_thread_safety(self):
        """Test that IOMetrics works correctly across different event loops in threads.

        This test creates a new event loop in a separate thread and attempts to
        use IOMetrics from that thread. If the lock is bound to the wrong event
        loop, this will fail with RuntimeError.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()
        errors = []
        success_count = [0]

        def worker_in_new_event_loop():
            """Worker function that creates its own event loop."""
            try:
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Try to use IOMetrics from this thread
                async def record_ops():
                    # This should get or create a lock for THIS event loop
                    await metrics.record_operation_async(
                        "write",
                        duration=0.2,
                        retries=0,
                        success=True
                    )
                    success_count[0] += 1

                # Run in this thread's event loop
                loop.run_until_complete(record_ops())
                loop.close()

            except Exception as e:
                errors.append(f"Worker error: {type(e).__name__}: {e}")

        # Start thread with its own event loop
        thread = threading.Thread(target=worker_in_new_event_loop)
        thread.start()
        thread.join(timeout=5.0)

        # Should not have any errors
        assert len(errors) == 0, f"Errors occurred in thread: {errors}"
        assert success_count[0] > 0, "Operation should have succeeded in thread"

    @pytest.mark.asyncio
    async def test_lock_initialization_race_condition(self):
        """Test that lock initialization is thread-safe.

        This test simulates the race condition where multiple threads try to
        initialize the lock simultaneously.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()
        errors = []
        results = []

        def worker(worker_id):
            """Worker that tries to get the async lock."""
            try:
                # Each worker creates its own event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def get_lock():
                    # Try to get the lock
                    lock = metrics._get_async_lock()
                    results.append(f"Worker {worker_id} got lock: {type(lock).__name__}")
                    # Try to use it
                    async with lock:
                        await metrics.record_operation_async(
                            f"op_{worker_id}",
                            duration=0.1,
                            retries=0,
                            success=True
                        )

                loop.run_until_complete(get_lock())
                loop.close()

            except Exception as e:
                errors.append(f"Worker {worker_id} error: {type(e).__name__}: {e}")

        # Start multiple threads simultaneously
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10.0)

        # Should not have any errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5, f"Expected 5 successful workers, got {len(results)}"

    @pytest.mark.asyncio
    async def test_lock_cannot_be_shared_across_event_loops(self):
        """Test that an asyncio.Lock cannot be used across different event loops.

        This is a demonstration of WHY the bug exists - asyncio.Lock instances
        are bound to the event loop they were created in.
        """
        # Create a lock in current loop
        lock1 = asyncio.Lock()
        current_loop = asyncio.get_running_loop()

        # Verify lock belongs to current loop
        assert lock1._loop is current_loop or hasattr(lock1, '_loop')

        # Try to use it in a different loop (will fail)
        errors = []

        def try_in_different_loop():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)

                async def try_use_lock():
                    # This will fail because lock1 is bound to a different loop
                    async with lock1:
                        pass

                new_loop.run_until_complete(try_use_lock())
            except RuntimeError as e:
                errors.append(str(e))
            finally:
                new_loop.close()

        thread = threading.Thread(target=try_in_different_loop)
        thread.start()
        thread.join(timeout=5.0)

        # Should get an error about wrong event loop
        assert len(errors) > 0, "Expected RuntimeError when using lock across event loops"

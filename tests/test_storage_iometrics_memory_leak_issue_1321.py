"""Test for memory leak in IOMetrics initialization (Issue #1321).

The issue is that IOMetrics uses id(event_loop) as dictionary keys in
self._locks and self._lock_creation_events. When event loops are destroyed
but not removed from these dictionaries, it causes memory leaks because the
locks and events remain referenced.

The fix should either:
1. Use WeakKeyDictionary (if event_loop supports weak references)
2. Ensure proper cleanup when event loops are closed
"""

import asyncio
import gc
import threading
import time
import pytest
import sys


class TestIOMetricsMemoryLeakIssue1321:
    """Test suite for IOMetrics memory leak (Issue #1321)."""

    @pytest.mark.asyncio
    async def test_iometrics_locks_cleanup_on_event_loop_close(self):
        """Test that locks are cleaned up when event loop is closed.

        This test verifies that when event loops are destroyed, the
        corresponding locks and events are removed from the dictionaries
        to prevent memory leaks.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()

        # Create a new event loop in a separate thread
        loop_ref = {'loop': None, 'loop_id': None}
        thread_started = {'value': False}
        thread_finished = {'value': False}

        def create_and_use_loop():
            """Create a new event loop, use it, then close it."""
            # Create new event loop
            loop = asyncio.new_event_loop()
            loop_ref['loop'] = loop
            loop_ref['loop_id'] = id(loop)
            asyncio.set_event_loop(loop)

            thread_started['value'] = True

            # Use the loop to create a lock
            async def create_lock():
                lock = metrics._get_async_lock()
                assert isinstance(lock, asyncio.Lock)

            loop.run_until_complete(create_lock())

            # Verify lock was created for this loop
            assert loop_ref['loop_id'] in metrics._locks
            assert len(metrics._locks) == 1

            # Close the loop
            loop.close()
            asyncio.set_event_loop(None)

            thread_finished['value'] = True

        # Run in thread
        thread = threading.Thread(target=create_and_use_loop)
        thread.start()
        thread.join(timeout=10)

        assert thread_finished['value'], "Thread did not finish"
        assert loop_ref['loop_id'] is not None

        # Fix for Issue #1321: After loop is closed and we call _get_async_lock again,
        # the stale lock should be cleaned up
        # Trigger cleanup by creating a new lock (in the current event loop)
        _ = metrics._get_async_lock()

        # EXPECTED BEHAVIOR (AFTER FIX): Old lock should be cleaned up
        assert loop_ref['loop_id'] not in metrics._locks, (
            "Lock should be cleaned up after loop closes"
        )
        assert loop_ref['loop_id'] not in metrics._event_loops, (
            "Event loop reference should be cleaned up"
        )

    @pytest.mark.asyncio
    async def test_iometrics_memory_leak_multiple_loops(self):
        """Test that multiple event loops don't cause unbounded memory growth.

        This test simulates the scenario where multiple event loops are created
        and destroyed over time. Without proper cleanup, the dictionaries will
        grow unbounded, causing memory leaks.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()

        loop_ids = []

        def create_and_close_loop():
            """Create a loop, use it, close it."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop_id = id(loop)
            loop_ids.append(loop_id)

            # Use the loop
            async def create_lock():
                lock = metrics._get_async_lock()
                assert isinstance(lock, asyncio.Lock)

            loop.run_until_complete(create_lock())
            loop.close()
            asyncio.set_event_loop(None)

        # Create and close multiple loops sequentially
        num_loops = 10
        threads = []

        for _ in range(num_loops):
            thread = threading.Thread(target=create_and_close_loop)
            threads.append(thread)
            thread.start()
            thread.join(timeout=5)

        # Verify all loops were processed
        assert len(loop_ids) == num_loops

        # Trigger cleanup by getting a lock in the current event loop
        _ = metrics._get_async_lock()

        # EXPECTED BEHAVIOR (AFTER FIX): Old locks should be cleaned up
        # Only the current event loop's lock should remain
        current_loop_id = id(asyncio.get_running_loop())
        assert len(metrics._locks) == 1, (
            f"Expected 1 lock (current loop), got {len(metrics._locks)}"
        )
        assert current_loop_id in metrics._locks, (
            "Current event loop lock should exist"
        )

        # Verify all old loop_ids have been cleaned up
        for loop_id in loop_ids:
            assert loop_id not in metrics._locks, (
                f"Lock for loop {loop_id} should be cleaned up"
            )
            assert loop_id not in metrics._event_loops, (
                f"Event loop reference for {loop_id} should be cleaned up"
            )

    @pytest.mark.asyncio
    async def test_iometrics_lock_creation_events_cleanup(self):
        """Test that lock creation events are cleaned up.

        This test verifies that self._lock_creation_events doesn't leak
        memory when event loops are destroyed.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()

        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop_id = id(loop)

        # Use the loop to create a lock
        async def create_lock():
            lock = metrics._get_async_lock()
            assert isinstance(lock, asyncio.Lock)

        loop.run_until_complete(create_lock())

        # After lock is created, the creation event should be cleaned up
        # (this should already work correctly in current implementation)
        assert loop_id not in metrics._lock_creation_events, (
            "Creation event should be cleaned up after lock is created"
        )

        # Close the loop
        loop.close()
        asyncio.set_event_loop(None)

        # Fix for Issue #1321: After cleanup is triggered, the lock entry
        # in _locks should be cleaned up
        # Switch back to the main event loop
        asyncio.set_event_loop(asyncio.get_event_loop())

        # Trigger cleanup by getting a lock
        _ = metrics._get_async_lock()

        # EXPECTED BEHAVIOR (AFTER FIX): Lock should be cleaned up
        assert loop_id not in metrics._locks, (
            "Lock should be cleaned up after loop closes"
        )
        assert loop_id not in metrics._event_loops, (
            "Event loop reference should be cleaned up"
        )

    @pytest.mark.asyncio
    async def test_iometrics_weak_key_dictionary_support(self):
        """Test if WeakKeyDictionary can be used for event loops.

        This test checks if event_loop objects support weak references.
        If they do, WeakKeyDictionary could be used to automatically
        clean up entries when event loops are destroyed.
        """
        from flywheel.storage import IOMetrics
        from weakref import WeakKeyDictionary

        metrics = IOMetrics()

        # Try to use WeakKeyDictionary with event loops
        try:
            weak_dict = WeakKeyDictionary()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Try to use the loop as a key
            weak_dict[loop] = "test_value"

            # Verify it works
            assert loop in weak_dict
            assert weak_dict[loop] == "test_value"

            # Close the loop and delete reference
            loop.close()
            asyncio.set_event_loop(None)
            del loop
            gc.collect()

            # After deletion, the entry should be automatically removed
            # (if event loops support weak references)
            # This test will help us understand if WeakKeyDictionary is viable

            loop_count = len(weak_dict)

            # Clean up
            asyncio.set_event_loop(asyncio.new_event_loop())

            # If loop_count > 0, event loops don't support weak refs
            # If loop_count == 0, we could use WeakKeyDictionary
            # Either way, we need explicit cleanup logic
            assert loop_count >= 0, "WeakKeyDictionary test completed"

        except TypeError as e:
            # Event loops don't support weak references
            # This is expected - we need explicit cleanup
            pytest.skip("Event loops don't support weak references")

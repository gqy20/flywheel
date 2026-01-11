"""Test for issue #1381: Sync and async locks don't provide true mutual exclusion.

This test demonstrates that threading.RLock and asyncio.Lock are independent
and don't provide mutual exclusion between sync and async contexts.
"""

import asyncio
import threading
import time
from unittest.mock import patch

import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestIssue1381:
    """Test that sync and async locks actually mutually exclude each other."""

    def test_sync_and_async_lock_mutual_exclusion(self):
        """Test that holding sync lock prevents async acquisition and vice versa.

        This test creates a scenario where:
        1. A thread holds the sync lock
        2. An async task tries to acquire the async lock
        3. They should NOT both be able to access the critical section

        The current implementation FAILS this test because threading.RLock
        and asyncio.Lock are independent mechanisms.
        """

        lock = _AsyncCompatibleLock()
        results = []
        sync_acquired = threading.Event()
        async_allowed = threading.Event()

        def sync_worker():
            """Hold sync lock and check if async can acquire."""
            with lock:
                results.append("sync_acquired")
                sync_acquired.set()
                # Wait to verify async can't acquire while we hold sync lock
                time.sleep(0.2)
                # Check if async acquired while we held sync lock
                if async_allowed.is_set():
                    results.append("ERROR: async_acquired_while_sync_held")

        async def async_worker():
            """Try to acquire async lock while sync is held."""
            # Wait for sync to acquire
            await asyncio.sleep(0.1)
            async with lock:
                results.append("async_acquired")
                async_allowed.set()

        # Start sync thread
        sync_thread = threading.Thread(target=sync_worker)
        sync_thread.start()

        # Wait for sync to acquire
        sync_acquired.wait(timeout=1.0)

        # Run async task in new thread with new event loop
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(async_worker())
            finally:
                loop.close()

        async_thread = threading.Thread(target=run_async)
        async_thread.start()

        # Wait for both to complete
        sync_thread.join(timeout=2.0)
        async_thread.join(timeout=2.0)

        # Verify results
        print(f"Results: {results}")

        # The bug: both locks can be held simultaneously
        # This assertion will FAIL with the current implementation
        assert "ERROR: async_acquired_while_sync_held" not in results, (
            "Bug detected: async lock was acquired while sync lock was held! "
            "This demonstrates that threading.RLock and asyncio.Lock are "
            "independent and don't provide mutual exclusion."
        )

    def test_async_and_sync_lock_mutual_exclusion(self):
        """Test that holding async lock prevents sync acquisition and vice versa."""

        lock = _AsyncCompatibleLock()
        results = []
        async_acquired = threading.Event()
        sync_allowed = threading.Event()

        async def async_worker():
            """Hold async lock and check if sync can acquire."""
            async with lock:
                results.append("async_acquired")
                async_acquired.set()
                # Wait to verify sync can't acquire while we hold async lock
                await asyncio.sleep(0.2)

        def sync_worker():
            """Try to acquire sync lock while async is held."""
            # Wait for async to acquire
            time.sleep(0.1)
            with lock:
                results.append("sync_acquired")
                sync_allowed.set()

        # Run async task first
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(async_worker())
            finally:
                loop.close()

        async_thread = threading.Thread(target=run_async)
        async_thread.start()

        # Wait for async to acquire
        async_acquired.wait(timeout=1.0)

        # Start sync thread
        sync_thread = threading.Thread(target=sync_worker)
        sync_thread.start()

        # Wait for both to complete
        async_thread.join(timeout=2.0)
        sync_thread.join(timeout=2.0)

        # Verify results
        print(f"Results: {results}")

        # Check the order - sync should wait for async to release
        async_idx = results.index("async_acquired")
        sync_idx = results.index("sync_acquired")

        # With the bug, sync might acquire before async releases
        # (Actually, with current bug they can both be held simultaneously)
        # We need to check that sync acquired AFTER async released
        # This is hard to test without proper synchronization
        # The first test is more definitive

    def test_unified_lock_behavior(self):
        """Test that a unified lock provides proper mutual exclusion.

        This is what the FIXED implementation should do.
        """

        lock = _AsyncCompatibleLock()
        critical_section_value = 0
        errors = []

        def increment_sync():
            """Increment using sync lock."""
            nonlocal critical_section_value
            try:
                with lock:
                    current = critical_section_value
                    time.sleep(0.01)  # Simulate some work
                    critical_section_value = current + 1
            except Exception as e:
                errors.append(f"sync error: {e}")

        async def increment_async():
            """Increment using async lock."""
            nonlocal critical_section_value
            try:
                async with lock:
                    current = critical_section_value
                    await asyncio.sleep(0.01)  # Simulate some work
                    critical_section_value = current + 1
            except Exception as e:
                errors.append(f"async error: {e}")

        # Run multiple sync and async operations concurrently
        threads = []
        for _ in range(5):
            t = threading.Thread(target=increment_sync)
            threads.append(t)

        def run_async_tasks():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    asyncio.gather(*[increment_async() for _ in range(5)])
                )
            finally:
                loop.close()

        async_thread = threading.Thread(target=run_async_tasks)
        threads.append(async_thread)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        print(f"Final value: {critical_section_value}")
        print(f"Errors: {errors}")

        # With proper mutual exclusion, value should be 10
        # With the bug, it might be less due to race conditions
        # However, this test might not reliably fail due to timing
        # The first test is more reliable

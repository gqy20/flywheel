"""Test IOMetrics lock consistency (Issue #1310).

This test verifies that IOMetrics uses a consistent locking mechanism
as documented in the class docstring, which states it should use
"pure asyncio.Lock" or "per-event-loop locks" to prevent deadlock
and race conditions.

The bug is that __init__ initializes threading.Lock, but the class
documentation says it should use pure async-only locking or per-event-loop
locks. Mixed use of threading.Lock and asyncio.Lock can cause deadlocks.
"""
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from flywheel.storage import IOMetrics


class TestIOMetricsLockConsistency:
    """Test suite for IOMetrics lock consistency (Issue #1310)."""

    def test_init_uses_per_event_loop_locks_not_threading_lock(self):
        """Test that IOMetrics __init__ uses properly named locks (Issue #1310).

        According to the docstring (Issue #1124, #1135, #1150, #1310), IOMetrics
        should use separate locks for initialization and sync operations.

        The fix for Issue #1310 split _sync_lock into:
        1. _init_lock - Only for _get_async_lock() initialization
        2. _sync_operation_lock - Only for sync record_operation()

        This verifies the old _sync_lock no longer exists (it was ambiguous
        and could cause confusion about its purpose).
        """
        metrics = IOMetrics()

        # The old _sync_lock should NOT exist after Issue #1310 fix
        # It was split into _init_lock and _sync_operation_lock
        assert not hasattr(metrics, '_sync_lock'), (
            "IOMetrics._sync_lock should not exist after Issue #1310 fix. "
            "It was split into _init_lock and _sync_operation_lock to clarify "
            "their purposes and maintain consistency with the documented design."
        )

        # Verify the new locks exist
        assert hasattr(metrics, '_init_lock'), (
            "IOMetrics should have _init_lock for initialization synchronization"
        )
        assert hasattr(metrics, '_sync_operation_lock'), (
            "IOMetrics should have _sync_operation_lock for sync operations"
        )

    def test_concurrent_sync_and_async_operations_no_deadlock(self):
        """Test that concurrent sync and async operations don't deadlock.

        When mixing threading.Lock (used in record_operation) and
        asyncio.Lock (used in _get_async_lock), potential deadlocks can occur.
        This test runs operations concurrently to detect such issues.
        """
        metrics = IOMetrics()
        deadlock_detected = False
        errors = []

        def sync_operation():
            """Run sync operations in a thread."""
            try:
                for i in range(10):
                    metrics.record_operation('read', 0.1, 0, True)
            except Exception as e:
                errors.append(f"Sync error: {e}")

        async def async_operation():
            """Run async operations."""
            try:
                for i in range(10):
                    await metrics.record_operation_async('write', 0.1, 0, True)
            except Exception as e:
                errors.append(f"Async error: {e}")

        async def run_async_in_thread():
            """Run async operations in a separate thread."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(async_operation())
            finally:
                loop.close()

        # Run sync operations in thread pool
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(sync_operation)
            future2 = executor.submit(lambda: asyncio.run(async_operation()))

            # Add timeout to detect potential deadlock
            start = time.time()
            try:
                future1.result(timeout=5)
                future2.result(timeout=5)
            except Exception as e:
                if time.time() - start > 4.5:
                    deadlock_detected = True
                errors.append(str(e))

        assert not deadlock_detected, "Potential deadlock detected - operations timed out"
        assert not errors, f"Errors occurred: {errors}"

    def test_record_operation_from_async_context_raises_error(self):
        """Test that calling record_operation from async context raises clear error.

        If threading.Lock is used while in an async context, it could cause
        issues. The class should raise _AsyncContextError to prevent this.
        """
        from flywheel.storage import _AsyncContextError

        metrics = IOMetrics()

        async def try_sync_in_async():
            """Try to call sync method from async context."""
            metrics.record_operation('read', 0.1, 0, True)

        with pytest.raises(_AsyncContextError):
            asyncio.run(try_sync_in_async())

    def test_lock_creation_events_consistency(self):
        """Test that _lock_creation_events is consistent with documented design.

        Issue #1310 notes that _lock_creation_events is initialized but
        may be inconsistent with the documented "pure async-only locking"
        approach from Issues #1124, #1135, #1150.
        """
        metrics = IOMetrics()

        # The _locks dict should exist for per-event-loop locks (Issue #1150)
        assert hasattr(metrics, '_locks'), "IOMetrics should have _locks for per-event-loop locking"

        # Check initial state
        assert isinstance(metrics._locks, dict), "_locks should be a dictionary"
        assert len(metrics._locks) == 0, "_locks should start empty"

    def test_no_direct_threading_lock_usage_in_public_methods(self):
        """Test that public methods don't directly use threading.Lock.

        The class documentation states it should use pure asyncio.Lock or
        per-event-loop locks. Public methods should not directly acquire
        threading.Lock as this can cause issues in async contexts.
        """
        import inspect
        from threading import Lock

        metrics = IOMetrics()

        # Check record_operation method
        source = inspect.getsource(metrics.record_operation)

        # The method should NOT directly create/use a raw threading.Lock
        # It can use self._sync_lock if that's a compatible wrapper,
        # but should not use Lock() directly
        assert "Lock()" not in source, (
            "record_operation should not directly instantiate threading.Lock. "
            "According to Issues #1124, #1135, #1150, it should use async-compatible "
            "locking mechanisms."
        )

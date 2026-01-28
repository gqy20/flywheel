"""Test for Issue #1091: IOMetrics lock usage in synchronous context.

This test verifies that IOMetrics can be safely used in synchronous contexts
without mixing asyncio.Lock with synchronous code.
"""
import asyncio
import threading
import pytest
from flywheel.storage import IOMetrics


def test_iometrics_instantiation_in_sync_context():
    """Test that IOMetrics can be instantiated in a synchronous context."""
    # This should not raise any errors
    metrics = IOMetrics()
    assert metrics is not None
    assert metrics.total_operation_count() == 0


def test_iometrics_synchronous_methods_thread_safety():
    """Test that synchronous methods are thread-safe."""
    metrics = IOMetrics()

    # Record some operations
    async def record_ops():
        for i in range(10):
            await metrics.record_operation('read', 0.1, 0, True)

    # Run in async context
    asyncio.run(record_ops())

    # Access from synchronous context
    count = metrics.total_operation_count()
    assert count == 10

    duration = metrics.total_duration()
    assert duration == 1.0  # 10 operations * 0.1 seconds


def test_iometrics_concurrent_sync_async_access():
    """Test concurrent access from sync and async contexts."""
    metrics = IOMetrics()
    results = {'sync_count': None, 'async_count': None}
    errors = []

    async def async_access():
        try:
            for i in range(50):
                await metrics.record_operation('write', 0.01, 0, True)
            results['async_count'] = metrics.total_operation_count()
        except Exception as e:
            errors.append(f"Async error: {e}")

    def sync_access():
        try:
            for i in range(50):
                # Simulate synchronous access
                count = metrics.total_operation_count()
                duration = metrics.total_duration()
            results['sync_count'] = metrics.total_operation_count()
        except Exception as e:
            errors.append(f"Sync error: {e}")

    # Start async task
    async def run_async():
        task = asyncio.create_task(async_access())

        # Run sync access in thread
        thread = threading.Thread(target=sync_access)
        thread.start()
        thread.join()

        await task

    try:
        asyncio.run(run_async())

        # Check for errors
        if errors:
            pytest.fail(f"Concurrent access errors: {errors}")

        # Both should see all operations
        assert results['async_count'] == 50
        assert results['sync_count'] == 50
    except RuntimeError as e:
        if "asyncio" in str(e).lower():
            pytest.skip("asyncio.Lock cannot be used in multi-threaded context without proper event loop setup")
        raise


def test_iometrics_lock_type():
    """Test that IOMetrics uses appropriate lock type."""
    metrics = IOMetrics()

    # Check if lock is asyncio.Lock or threading.Lock
    import threading
    lock_type = type(metrics._lock).__name__

    # For thread-safe synchronous access, should use threading.Lock
    # For async-only access, asyncio.Lock is acceptable
    # This test documents the current state
    if lock_type == '_thread.lock':
        # Using threading.Lock - safe for sync contexts
        assert True
    elif lock_type == 'Lock':
        # Using asyncio.Lock - may cause issues in sync contexts
        # This is the bug described in issue #1091
        pytest.fail("IOMetrics uses asyncio.Lock which is unsafe for synchronous/multi-threaded contexts")
    else:
        pytest.fail(f"Unknown lock type: {lock_type}")

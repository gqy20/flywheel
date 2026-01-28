"""Test for Issue #1097: Fix sync/async lock mismatch in IOMetrics.

This test verifies that IOMetrics correctly uses async locks in async contexts.
The issue was that __init__ used threading.Lock() while export_to_dict used
async with self._lock, which causes RuntimeError.
"""

import asyncio
import pytest
from flywheel.storage import IOMetrics


def test_iometrics_async_lock_compatibility():
    """Test that IOMetrics lock works correctly in async context.

    This test ensures that the lock used in IOMetrics supports both
    synchronous and asynchronous context managers.
    """
    metrics = IOMetrics()

    async def test_async_operations():
        # Record some operations
        await metrics.record_operation('read', 0.1, 0, True)
        await metrics.record_operation('write', 0.2, 1, False, 'ENOENT')

        # Test export_to_dict which uses async with
        result = metrics.export_to_dict()

        # Verify the export worked correctly
        assert result['total_operation_count'] == 2
        assert result['successful_operations'] == 1
        assert result['failed_operations'] == 1
        assert result['total_retries'] == 1
        return result

    # Run the async test
    result = asyncio.run(test_async_operations())
    assert result is not None


def test_iometrics_sync_lock_compatibility():
    """Test that IOMetrics lock works correctly in sync context.

    This test ensures that the lock used in IOMetrics supports
    synchronous context managers as well.
    """
    metrics = IOMetrics()

    async def record_ops():
        await metrics.record_operation('read', 0.1, 0, True)
        await metrics.record_operation('read', 0.15, 0, True)

    # Record operations
    asyncio.run(record_ops())

    # Test synchronous methods that use 'with self._lock'
    count = metrics.total_operation_count()
    duration = metrics.total_duration()

    assert count == 2
    assert duration == 0.25


def test_iometrics_concurrent_access():
    """Test that IOMetrics handles concurrent access safely.

    This test verifies that the lock properly protects against
    race conditions when multiple coroutines access the metrics.
    """
    metrics = IOMetrics()

    async def concurrent_operations():
        # Create multiple concurrent tasks
        tasks = [
            metrics.record_operation('read', 0.1, i % 3, i % 2 == 0)
            for i in range(10)
        ]

        # Also try to export concurrently
        async def export_once():
            return metrics.export_to_dict()

        export_tasks = [
            export_once()
            for _ in range(5)
        ]

        # Run all tasks concurrently
        await asyncio.gather(*tasks, *export_tasks)

        # Get final result
        result = metrics.export_to_dict()
        return result

    result = asyncio.run(concurrent_operations())

    # Should have recorded 10 operations
    assert result['total_operation_count'] == 10
    assert result['total_retries'] == sum(i % 3 for i in range(10))


def test_iometrics_lock_type():
    """Test that IOMetrics uses the correct lock type.

    This test verifies that the lock instance supports both
    sync and async context managers.
    """
    metrics = IOMetrics()

    # Check that the lock has __aenter__ and __aexit__ methods
    # (required for async context manager support)
    assert hasattr(metrics._lock, '__aenter__'), \
        "Lock must support async context manager protocol (__aenter__)"
    assert hasattr(metrics._lock, '__aexit__'), \
        "Lock must support async context manager protocol (__aexit__)"

    # Also check for sync context manager support
    assert hasattr(metrics._lock, '__enter__'), \
        "Lock should support sync context manager protocol (__enter__)"
    assert hasattr(metrics._lock, '__exit__'), \
        "Lock should support sync context manager protocol (__exit__)"

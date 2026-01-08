"""Test for Issue #1109: IOMetrics.record_operation should work in async contexts."""

import asyncio
import pytest
from flywheel.storage import IOMetrics


def test_record_operation_in_async_context():
    """Test that record_operation can be called from within an async context.

    This test reproduces Issue #1109 where calling a synchronous method
    that uses _AsyncCompatibleLock from within an async context raises
    RuntimeError.
    """
    metrics = IOMetrics()

    async def async_operation():
        # Simulate being called from an async context (e.g., Jupyter, FastAPI, etc.)
        # This should NOT raise RuntimeError
        metrics.record_operation(
            operation_type='read',
            duration=0.1,
            retries=0,
            success=True
        )

    # Run the async function which has a running event loop
    asyncio.run(async_operation())

    # Verify the operation was recorded
    assert metrics.total_operation_count() == 1
    assert metrics.total_duration() == 0.1


def test_record_operation_in_sync_context():
    """Test that record_operation still works in normal sync context."""
    metrics = IOMetrics()

    # Normal synchronous usage should work
    metrics.record_operation(
        operation_type='write',
        duration=0.2,
        retries=1,
        success=False,
        error_type='ENOENT'
    )

    assert metrics.total_operation_count() == 1
    assert metrics.total_duration() == 0.2


def test_multiple_operations_in_async_context():
    """Test multiple record_operation calls from async context."""
    metrics = IOMetrics()

    async def async_operations():
        # Multiple calls should all work
        for i in range(5):
            metrics.record_operation(
                operation_type='read',
                duration=0.1 * i,
                retries=0,
                success=True
            )

    asyncio.run(async_operations())

    assert metrics.total_operation_count() == 5
    assert metrics.total_duration() == 1.0  # 0 + 0.1 + 0.2 + 0.3 + 0.4

"""Test for Issue #1116: IOMetrics.record_operation async context deadlock.

This test verifies that record_operation can be safely called from async contexts
without causing deadlocks.
"""
import asyncio
import pytest

from flywheel.storage import IOMetrics


@pytest.mark.asyncio
async def test_record_operation_in_async_context():
    """Test that record_operation works in async context without deadlock.

    Issue #1116: record_operation uses threading.Lock which can cause
    deadlock when called from async contexts. This test calls it from
    an async context to verify it works correctly.
    """
    metrics = IOMetrics()

    # Record operation from async context
    metrics.record_operation("read", 0.1, 0, True)

    # Record multiple operations
    metrics.record_operation("write", 0.2, 0, True)
    metrics.record_operation("read", 0.15, 1, False, "ENOENT")

    # Verify operations were recorded
    assert len(metrics.operations) == 3


@pytest.mark.asyncio
async def test_record_operation_concurrent_async():
    """Test that record_operation works with concurrent async calls.

    This test verifies that multiple async tasks can call record_operation
    concurrently without causing deadlocks or data corruption.
    """
    metrics = IOMetrics()

    async def record_ops(task_id: int):
        """Record operations from an async task."""
        for i in range(10):
            metrics.record_operation(f"op_{task_id}", 0.01, 0, True)

    # Run multiple concurrent tasks
    tasks = [record_ops(i) for i in range(5)]
    await asyncio.gather(*tasks)

    # Should have 50 operations (5 tasks * 10 ops each)
    assert len(metrics.operations) == 50


@pytest.mark.asyncio
async def test_track_operation_async_context_manager():
    """Test that track_operation async context manager works correctly.

    This test uses the async context manager which internally calls
    record_operation, verifying the full async flow.
    """
    metrics = IOMetrics()

    async def simulate_io_operation():
        """Simulate an async I/O operation."""
        await asyncio.sleep(0.01)
        return "data"

    # Use the async context manager
    async with metrics.track_operation("read"):
        result = await simulate_io_operation()

    assert result == "data"
    assert len(metrics.operations) == 1
    assert metrics.operations[0]['operation_type'] == "read"
    assert metrics.operations[0]['success'] is True


@pytest.mark.asyncio
async def test_track_operation_async_with_failure():
    """Test that track_operation records failures in async context."""
    metrics = IOMetrics()

    async def failing_operation():
        """Simulate a failing async operation."""
        await asyncio.sleep(0.01)
        raise ValueError("Test error")

    # Use the async context manager with a failing operation
    try:
        async with metrics.track_operation("write"):
            await failing_operation()
    except ValueError:
        pass  # Expected error

    assert len(metrics.operations) == 1
    assert metrics.operations[0]['operation_type'] == "write"
    assert metrics.operations[0]['success'] is False
    assert metrics.operations[0]['error_type'] == "ValueError"

"""Test for IOMetrics async/sync lock usage fix (Issue #1087)."""
import asyncio
import pytest

from flywheel.storage import IOMetrics


@pytest.mark.asyncio
async def test_export_to_dict_async_lock_usage():
    """Test that export_to_dict can be called without RuntimeError.

    The export_to_dict method was using 'with self._lock' (sync context manager)
    on an asyncio.Lock, which causes RuntimeError. This test verifies the fix
    by calling export_to_dict and ensuring it doesn't raise an error.

    Related: Issue #1087
    """
    metrics = IOMetrics()

    # Record some operations
    await metrics.record_operation('read', 0.5, 0, True)
    await metrics.record_operation('write', 0.3, 1, True)
    await metrics.record_operation('flush', 0.2, 0, False, error_type='EIO')

    # This should not raise RuntimeError about using sync context manager on asyncio.Lock
    result = metrics.export_to_dict()

    # Verify the export worked correctly
    assert result['total_operation_count'] == 3
    assert result['successful_operations'] == 2
    assert result['failed_operations'] == 1
    assert result['total_retries'] == 1
    assert len(result['operations']) == 3


@pytest.mark.asyncio
async def test_export_to_dict_concurrent_access():
    """Test that export_to_dict is thread-safe under concurrent access.

    Multiple coroutines should be able to call export_to_dict simultaneously
    without causing race conditions or errors.

    Related: Issue #1087
    """
    metrics = IOMetrics()

    # Record some operations
    for i in range(10):
        await metrics.record_operation('read', 0.1, 0, True)

    # Create async wrapper functions for concurrent export
    async def export_once():
        return metrics.export_to_dict()

    # Create tasks for concurrent export
    tasks = [export_once() for _ in range(5)]

    # All should complete without error
    results = await asyncio.gather(*tasks)

    # All results should be consistent
    for result in results:
        assert result['total_operation_count'] == 10
        assert result['successful_operations'] == 10
        assert result['failed_operations'] == 0


@pytest.mark.asyncio
async def test_export_to_dict_empty_metrics():
    """Test that export_to_dict works correctly with empty metrics.

    Related: Issue #1087
    """
    metrics = IOMetrics()

    result = metrics.export_to_dict()

    assert result['total_operation_count'] == 0
    assert result['successful_operations'] == 0
    assert result['failed_operations'] == 0
    assert result['total_retries'] == 0
    assert result['total_duration'] == 0.0
    assert result['operations'] == []

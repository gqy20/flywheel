"""Tests for Issue #1149: IOMetrics.record_operation async context deadlock detection.

This test ensures that calling record_operation from an async context
properly raises _AsyncContextError to prevent deadlocks.
"""

import asyncio
import pytest

from flywheel.storage import IOMetrics, _AsyncContextError


def test_record_operation_in_async_context_raises_error():
    """Test that record_operation raises _AsyncContextError in async context."""
    metrics = IOMetrics(max_size=100)

    async def call_in_async_context():
        # This should raise _AsyncContextError
        metrics.record_operation(
            operation_type='read',
            duration=0.1,
            retries=0,
            success=True
        )

    # Run the async function and expect _AsyncContextError
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        with pytest.raises(_AsyncContextError) as exc_info:
            loop.run_until_complete(call_in_async_context())

        # Verify the error message mentions using the async version
        assert "record_operation_async" in str(exc_info.value)
        assert "async context" in str(exc_info.value).lower()
    finally:
        loop.close()


def test_record_operation_in_sync_context_works():
    """Test that record_operation works in sync context."""
    metrics = IOMetrics(max_size=100)

    # This should work fine in sync context
    metrics.record_operation(
        operation_type='read',
        duration=0.1,
        retries=0,
        success=True
    )

    # Verify the operation was recorded
    assert len(metrics.operations) == 1
    assert metrics.operations[0]['operation_type'] == 'read'


def test_record_operation_async_in_async_context():
    """Test that record_operation_async works in async context."""
    metrics = IOMetrics(max_size=100)

    async def call_async_method():
        await metrics.record_operation_async(
            operation_type='read',
            duration=0.1,
            retries=0,
            success=True
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(call_async_method())

        # Verify the operation was recorded
        assert len(metrics.operations) == 1
        assert metrics.operations[0]['operation_type'] == 'read'
    finally:
        loop.close()


def test_record_operation_from_thread_with_event_loop():
    """Test that record_operation properly detects async context when called from thread with running loop."""
    import threading
    results = {'error': None, 'success': False}

    def async_worker():
        """Worker that runs an event loop."""
        async def async_task():
            # Simulate an async context
            await asyncio.sleep(0.01)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_task())
            results['loop_running'] = True
        finally:
            loop.close()

    def sync_caller():
        """Thread that tries to call record_operation while another thread has a loop."""
        # This should work because we're not in an async context
        metrics = IOMetrics(max_size=100)
        try:
            metrics.record_operation(
                operation_type='read',
                duration=0.1,
                retries=0,
                success=True
            )
            results['success'] = True
        except Exception as e:
            results['error'] = e

    # Start async worker thread
    async_thread = threading.Thread(target=async_worker)
    async_thread.start()

    # Wait a bit for the event loop to start
    import time
    time.sleep(0.005)

    # Try to call from sync context
    sync_caller()

    # Wait for async thread to finish
    async_thread.join()

    # Should succeed because we're not in an async context
    assert results['success'], f"Expected success but got error: {results['error']}"

"""Tests for Issue #1022 - Refactor statsd metrics sending to reduce duplication.

ISSUE #1022 requests that the statsd metrics sending logic be extracted
from async_wrapper and sync_wrapper into a helper function _record_metrics().

This test verifies that:
1. The _record_metrics helper function exists
2. The helper function correctly sends statsd metrics
3. The helper function correctly logs timing information
4. Both sync and async wrappers use the helper function
5. The refactored code maintains the same functionality
"""

import pytest
import time
from unittest.mock import patch, MagicMock, call
from flywheel.storage import measure_latency


class TestRecordMetricsHelperExists:
    """Test that _record_metrics helper function exists and is callable."""

    def test_helper_function_exists(self):
        """Test that _record_metrics function exists in storage module."""
        from flywheel import storage
        assert hasattr(storage, '_record_metrics'), \
            "_record_metrics helper function should exist"
        assert callable(storage._record_metrics), \
            "_record_metrics should be callable"

    def test_helper_function_signature(self):
        """Test that _record_metrics has the expected signature."""
        import inspect
        from flywheel import storage

        sig = inspect.signature(storage._record_metrics)
        params = list(sig.parameters.keys())

        # Should have parameters: operation_name, elapsed_ms, context
        assert 'operation_name' in params, \
            f"_record_metrics should have 'operation_name' parameter, got: {params}"
        assert 'elapsed_ms' in params, \
            f"_record_metrics should have 'elapsed_ms' parameter, got: {params}"
        assert 'context' in params, \
            f"_record_metrics should have 'context' parameter, got: {params}"


class TestRecordMetricsFunctionality:
    """Test that _record_metrics correctly handles metrics and logging."""

    def test_sends_statsd_timing_metric(self):
        """Test that _record_metrics sends timing metric to statsd."""
        from flywheel import storage

        # Mock statsd client
        mock_client = MagicMock()
        with patch('flywheel.storage.get_statsd_client', return_value=mock_client):
            with patch('flywheel.storage.logger') as mock_logger:
                storage._record_metrics("test_operation", 123.456, "[test.json]")

                # Verify timing was sent
                mock_client.timing.assert_called_once()
                call_args = mock_client.timing.call_args
                assert call_args[0][0] == "test_operation.latency"
                assert call_args[0][1] == 123.456

    def test_sends_histogram_when_supported(self):
        """Test that _record_metrics sends histogram when statsd supports it."""
        from flywheel import storage

        mock_client = MagicMock()
        mock_client.histogram = MagicMock()

        with patch('flywheel.storage.get_statsd_client', return_value=mock_client):
            with patch('flywheel.storage.logger') as mock_logger:
                storage._record_metrics("test_op", 100.0, "[id:123]")

                # Verify histogram was sent
                mock_client.histogram.assert_called_once()
                call_args = mock_client.histogram.call_args
                assert call_args[0][0] == "test_op.latency.dist"
                assert call_args[0][1] == 100.0

    def test_logs_timing_debug_message(self):
        """Test that _record_metrics logs debug message with timing."""
        from flywheel import storage

        with patch('flywheel.storage.get_statsd_client', return_value=None):
            with patch('flywheel.storage.logger') as mock_logger:
                storage._record_metrics("save", 456.789, "[/tmp/test.json]")

                # Verify debug log
                mock_logger.debug.assert_called()
                call_args = mock_logger.debug.call_args[0][0]
                assert "save" in call_args
                assert "/tmp/test.json" in call_args
                assert "456.789" in call_args or "456.78" in call_args or "456.7" in call_args
                assert "ms" in call_args

    def test_logs_slow_operation_warning(self):
        """Test that _record_metrics logs warning for slow operations."""
        from flywheel import storage

        # Set threshold to 100ms for testing
        with patch('flywheel.storage._get_slow_operation_threshold', return_value=100):
            with patch('flywheel.storage.get_statsd_client', return_value=None):
                with patch('flywheel.storage.logger') as mock_logger:
                    # Operation took 500ms, threshold is 100ms
                    storage._record_metrics("load", 500.0, "[id:42]")

                    # Verify warning was logged
                    mock_logger.warning.assert_called()
                    call_args = mock_logger.warning.call_args[0][0]
                    assert "load" in call_args
                    assert "id:42" in call_args
                    assert "500" in call_args
                    assert "exceeded slow threshold" in call_args

    def test_handles_no_statsd_client(self):
        """Test that _record_metrics works when statsd is not available."""
        from flywheel import storage

        # Simulate no statsd client
        with patch('flywheel.storage.get_statsd_client', return_value=None):
            with patch('flywheel.storage.logger') as mock_logger:
                # Should not raise an error
                storage._record_metrics("test", 100.0, "[]")

                # Should still log
                mock_logger.debug.assert_called()


class TestSyncWrapperUsesHelper:
    """Test that sync_wrapper uses the _record_metrics helper."""

    def test_sync_wrapper_calls_helper(self):
        """Test that sync_wrapper calls _record_metrics."""
        from flywheel import storage

        @measure_latency("sync_test")
        def sync_operation(path):
            time.sleep(0.01)
            return f"sync result for {path}"

        with patch('flywheel.storage._record_metrics') as mock_record:
            result = sync_operation("/tmp/test.json")

            # Verify function worked
            assert result == "sync result for /tmp/test.json"

            # Verify helper was called
            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args[0][0] == "sync_test"  # operation_name
            assert call_args[0][2] == "[/tmp/test.json]"  # context
            # elapsed_ms should be approximately 10-20ms
            elapsed = call_args[0][1]
            assert 5 < elapsed < 100, f"Expected elapsed between 5-100ms, got {elapsed}"


class TestAsyncWrapperUsesHelper:
    """Test that async_wrapper uses the _record_metrics helper."""

    def test_async_wrapper_calls_helper(self):
        """Test that async_wrapper calls _record_metrics."""
        import asyncio
        from flywheel import storage

        @measure_latency("async_test")
        async def async_operation(path):
            await asyncio.sleep(0.01)
            return f"async result for {path}"

        async def run_test():
            with patch('flywheel.storage._record_metrics') as mock_record:
                result = await async_operation("/tmp/async.json")

                # Verify function worked
                assert result == "async result for /tmp/async.json"

                # Verify helper was called
                mock_record.assert_called_once()
                call_args = mock_record.call_args
                assert call_args[0][0] == "async_test"  # operation_name
                assert call_args[0][2] == "[/tmp/async.json]"  # context
                # elapsed_ms should be approximately 10-20ms
                elapsed = call_args[0][1]
                assert 5 < elapsed < 100, f"Expected elapsed between 5-100ms, got {elapsed}"

        asyncio.run(run_test())


def test_issue_1022_refactor_complete():
    """Integration test verifying the refactor maintains functionality."""
    from flywheel import storage

    # Test that both sync and async work identically after refactor
    @measure_latency("sync_op")
    def sync_func():
        return "sync done"

    @measure_latency("async_op")
    async def async_func():
        return "async done"

    import asyncio

    # Test sync
    with patch('flywheel.storage._record_metrics') as mock_sync:
        result = sync_func()
        assert result == "sync done"
        mock_sync.assert_called_once()

    # Test async
    async def test_async():
        with patch('flywheel.storage._record_metrics') as mock_async:
            result = await async_func()
            assert result == "async done"
            mock_async.assert_called_once()

    asyncio.run(test_async())

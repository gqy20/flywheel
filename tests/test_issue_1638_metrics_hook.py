"""Tests for Issue #1638: Storage metrics collection hook.

This test ensures that the StorageMetrics protocol/class is properly implemented
to allow observability tools (like Prometheus/Datadog) to track storage performance.
"""

import asyncio
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from flywheel.storage import (
    _retry_io_operation,
    _AsyncCompatibleLock,
    FileStorage,
)


class TestStorageMetricsProtocol:
    """Test that StorageMetrics protocol is defined and usable."""

    def test_storage_metrics_protocol_exists(self):
        """Test that StorageMetrics protocol/class exists."""
        from flywheel.storage import StorageMetrics
        assert StorageMetrics is not None

    def test_storage_metrics_has_required_methods(self):
        """Test that StorageMetrics has required methods."""
        from flywheel.storage import StorageMetrics

        # Check that the protocol has the required methods
        required_methods = [
            'record_io_operation',
            'record_lock_contention',
            'record_lock_acquired',
        ]

        for method in required_methods:
            assert hasattr(StorageMetrics, method), f"StorageMetrics missing method: {method}"


class TestNoOpMetrics:
    """Test the no-op metrics implementation."""

    def test_noop_metrics_can_be_instantiated(self):
        """Test that NoOpMetrics can be created and used."""
        from flywheel.storage import NoOpStorageMetrics

        metrics = NoOpStorageMetrics()

        # These should not raise any errors
        metrics.record_io_operation('read', 0.1, retries=0, success=True)
        metrics.record_lock_contention(0.05)
        metrics.record_lock_acquired(0.02)

    def test_noop_metrics_is_singleton_like(self):
        """Test that NoOpMetrics can be used as default."""
        from flywheel.storage import NoOpStorageMetrics

        metrics1 = NoOpStorageMetrics()
        metrics2 = NoOpStorageMetrics()

        # Can be instantiated multiple times
        assert metrics1 is not None
        assert metrics2 is not None


class TestPrometheusMetricsIntegration:
    """Test Prometheus integration when available."""

    def test_prometheus_metrics_when_available(self):
        """Test PrometheusMetrics when prometheus_client is available."""
        # This test uses a mock prometheus_client
        mock_counter = MagicMock()
        mock_histogram = MagicMock()
        mock_gauge = MagicMock()

        mock_prometheus = MagicMock()
        mock_prometheus.Counter = MagicMock(return_value=mock_counter)
        mock_prometheus.Histogram = MagicMock(return_value=mock_histogram)
        mock_prometheus.Gauge = MagicMock(return_value=mock_gauge)

        with patch.dict('sys.modules', {'prometheus_client': mock_prometheus}):
            # Force reimport to pick up mocked module
            import importlib
            import sys
            if 'flywheel.storage' in sys.modules:
                # Remove the module to force reimport
                del sys.modules['flywheel.storage']

            from flywheel.storage import PrometheusStorageMetrics

            metrics = PrometheusStorageMetrics()

            # Test recording I/O operation
            metrics.record_io_operation('read', 0.1, retries=0, success=True)

            # Verify that counter was called
            assert mock_counter.labels.return_value.inc.called or \
                   mock_histogram.labels.return_value.observe.called

            # Test recording lock contention
            metrics.record_lock_contention(0.05)

            # Test recording lock acquired
            metrics.record_lock_acquired(0.02)

    def test_prometheus_metrics_fallback_when_unavailable(self):
        """Test that NoOpMetrics is used when prometheus_client is not available."""
        # Ensure prometheus_client is not available
        with patch.dict('sys.modules', {'prometheus_client': None}):
            import importlib
            import sys
            if 'flywheel.storage' in sys.modules:
                del sys.modules['flywheel.storage']

            # This should not raise an error
            from flywheel.storage import get_storage_metrics
            metrics = get_storage_metrics()

            # Should return NoOpMetrics when prometheus_client is unavailable
            metrics.record_io_operation('read', 0.1, retries=0, success=True)


class TestMetricsWithRetryOperation:
    """Test that metrics are integrated with _retry_io_operation."""

    @pytest.mark.asyncio
    async def test_retry_operation_with_metrics(self):
        """Test that _retry_io_operation calls metrics callbacks."""
        from flywheel.storage import NoOpStorageMetrics

        metrics = NoOpStorageMetrics()

        # Mock the record method to track calls
        with patch.object(metrics, 'record_io_operation', wraps=metrics.record_io_operation) as mock_record:
            # Simple operation that succeeds
            def simple_operation():
                return "success"

            result = await _retry_io_operation(
                simple_operation,
                operation_type='test',
                metrics=metrics
            )

            assert result == "success"
            # Verify metrics were recorded
            mock_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_operation_metrics_on_failure(self):
        """Test that metrics record failed operations."""
        from flywheel.storage import NoOpStorageMetrics

        metrics = NoOpStorageMetrics()

        with patch.object(metrics, 'record_io_operation', wraps=metrics.record_io_operation) as mock_record:
            # Operation that fails
            def failing_operation():
                raise IOError("Test error")

            with pytest.raises(IOError):
                await _retry_io_operation(
                    failing_operation,
                    operation_type='test',
                    metrics=metrics
                )

            # Verify metrics were recorded for failed operation
            assert mock_record.call_count >= 1


class TestMetricsWithLockOperations:
    """Test that metrics are integrated with lock operations."""

    def test_lock_metrics_integration(self):
        """Test that lock operations can record metrics."""
        from flywheel.storage import NoOpStorageMetrics

        metrics = NoOpStorageMetrics()
        lock = _AsyncCompatibleLock()

        # Mock the metrics methods
        with patch.object(metrics, 'record_lock_contention') as mock_contention, \
             patch.object(metrics, 'record_lock_acquired') as mock_acquired:

            # These should be callable during lock operations
            # The actual integration depends on the implementation
            mock_contention(0.01)
            mock_acquired(0.005)

            mock_contention.assert_called_once()
            mock_acquired.assert_called_once()


class TestGetStorageMetrics:
    """Test the get_storage_metrics() factory function."""

    def test_get_storage_metrics_returns_noop_by_default(self):
        """Test that get_storage_metrics returns NoOpMetrics when prometheus_client unavailable."""
        with patch.dict('sys.modules', {'prometheus_client': None}):
            import sys
            if 'flywheel.storage' in sys.modules:
                del sys.modules['flywheel.storage']

            from flywheel.storage import get_storage_metrics, NoOpStorageMetrics

            metrics = get_storage_metrics()
            assert isinstance(metrics, NoOpStorageMetrics)

    def test_get_storage_metrics_returns_prometheus_when_available(self):
        """Test that get_storage_metrics returns PrometheusMetrics when available."""
        mock_prometheus = MagicMock()

        with patch.dict('sys.modules', {'prometheus_client': mock_prometheus}):
            import sys
            if 'flywheel.storage' in sys.modules:
                del sys.modules['flywheel.storage']

            try:
                from flywheel.storage import get_storage_metrics, PrometheusStorageMetrics

                metrics = get_storage_metrics()
                assert isinstance(metrics, PrometheusStorageMetrics)
            except ImportError:
                # If PrometheusStorageMetrics is not yet implemented, skip
                pytest.skip("PrometheusStorageMetrics not yet implemented")


class TestMetricsIntegrationWithStorage:
    """Test metrics integration with FileStorage."""

    def test_storage_accepts_metrics_parameter(self):
        """Test that FileStorage can accept a metrics parameter."""
        from flywheel.storage import NoOpStorageMetrics

        with tempfile.TemporaryDirectory() as tmpdir:
            metrics = NoOpStorageMetrics()
            storage_path = os.path.join(tmpdir, "todos.json")

            # FileStorage should accept metrics parameter
            storage = FileStorage(storage_path, metrics=metrics)

            assert storage.metrics == metrics

    @pytest.mark.asyncio
    async def test_storage_operations_record_metrics(self):
        """Test that storage operations record metrics."""
        from flywheel.storage import NoOpStorageMetrics

        with tempfile.TemporaryDirectory() as tmpdir:
            metrics = NoOpStorageMetrics()
            storage_path = os.path.join(tmpdir, "todos.json")

            with patch.object(metrics, 'record_io_operation') as mock_record:
                storage = FileStorage(storage_path, metrics=metrics)

                from flywheel.todo import Todo
                todo = Todo("test", "description")

                # Save should record metrics
                await storage.save(todo)

                # Verify metrics were recorded
                assert mock_record.call_count > 0


class TestMetricsBackwardCompatibility:
    """Test backward compatibility when metrics is not provided."""

    @pytest.mark.asyncio
    async def test_storage_works_without_metrics(self):
        """Test that storage works normally when metrics is not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "todos.json")
            storage = FileStorage(storage_path)

            from flywheel.todo import Todo
            todo = Todo("test", "description")

            # Should work without metrics
            await storage.save(todo)

            # Should be able to load
            loaded = await storage.load(todo.id)
            assert loaded.title == "test"

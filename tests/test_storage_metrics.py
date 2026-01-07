"""Tests for storage latency metrics (Issue #1003)."""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


class TestStorageMetrics:
    """Test suite for storage latency metrics."""

    def test_load_emits_latency_metric(self, tmp_path):
        """Test that _load emits latency metric."""
        # Arrange
        storage_path = tmp_path / "todos.json"
        storage = FileStorage(str(storage_path))

        # Mock statsd client
        mock_statsd = mock.Mock()
        with mock.patch('flywheel.storage.get_statsd_client', return_value=mock_statsd):
            # Act
            storage._load_sync()

            # Assert
            # Verify that timing metric was called for _load operation
            mock_statsd.timing.assert_called()
            call_args = mock_statsd.timing.call_args_list
            assert len(call_args) > 0, "Expected timing metric to be emitted"

            # Check that the metric name contains 'load'
            metric_name = call_args[0][0][0]
            assert 'load' in metric_name.lower(), f"Expected 'load' in metric name, got {metric_name}"

            # Check that timing value is positive and reasonable (in milliseconds)
            timing_value = call_args[0][0][1]
            assert timing_value >= 0, "Timing value should be non-negative"
            assert timing_value < 60000, "Timing value should be less than 60 seconds"

    def test_save_emits_latency_metric(self, tmp_path):
        """Test that _save emits latency metric."""
        # Arrange
        storage_path = tmp_path / "todos.json"
        storage = FileStorage(str(storage_path))

        # Add a todo to trigger save
        todo = Todo(id=1, subject="Test todo")
        storage._todos = [todo]
        storage._dirty = True

        # Mock statsd client
        mock_statsd = mock.Mock()
        with mock.patch('flywheel.storage.get_statsd_client', return_value=mock_statsd):
            # Act - run async save in sync context
            asyncio.run(storage._save())

            # Assert
            # Verify that timing metric was called for _save operation
            mock_statsd.timing.assert_called()
            call_args = mock_statsd.timing.call_args_list

            # Check that the metric name contains 'save'
            metric_name = call_args[0][0][0]
            assert 'save' in metric_name.lower(), f"Expected 'save' in metric name, got {metric_name}"

            # Check that timing value is positive and reasonable
            timing_value = call_args[0][0][1]
            assert timing_value >= 0, "Timing value should be non-negative"

    def test_acquire_file_lock_emits_latency_metric(self, tmp_path):
        """Test that _acquire_file_lock emits latency metric."""
        # Arrange
        storage_path = tmp_path / "todos.json"
        storage = FileStorage(str(storage_path))

        # Mock statsd client
        mock_statsd = mock.Mock()
        with mock.patch('flywheel.storage.get_statsd_client', return_value=mock_statsd):
            # Create a test file and acquire lock
            with open(storage_path, 'w') as f:
                # Act
                storage._acquire_file_lock(f)

                # Assert
                # Verify that timing metric was called for lock acquisition
                mock_statsd.timing.assert_called()
                call_args = mock_statsd.timing.call_args_list

                # Check that the metric name contains 'lock'
                metric_names = [call[0][0] for call in call_args]
                lock_metrics = [name for name in metric_names if 'lock' in name.lower()]
                assert len(lock_metrics) > 0, "Expected lock acquisition metric to be emitted"

    def test_metrics_emitted_without_statsd_client(self, tmp_path, caplog):
        """Test that operations work normally when statsd client is not available."""
        # Arrange
        storage_path = tmp_path / "todos.json"
        storage = FileStorage(str(storage_path))

        # Mock get_statsd_client to return None
        with mock.patch('flywheel.storage.get_statsd_client', return_value=None):
            # Act & Assert - should not raise an error
            storage._load_sync()  # Should complete without error

            # Add a todo and save
            todo = Todo(id=1, subject="Test todo")
            storage._todos = [todo]
            storage._dirty = True
            asyncio.run(storage._save())  # Should complete without error

    def test_metrics_decorator_measures_execution_time(self, tmp_path):
        """Test that the metrics decorator accurately measures execution time."""
        # Arrange
        storage_path = tmp_path / "todos.json"
        storage = FileStorage(str(storage_path))

        # Mock statsd client
        mock_statsd = mock.Mock()

        # Create a delay to test timing accuracy
        def slow_load():
            time.sleep(0.1)  # Sleep for 100ms

        with mock.patch('flywheel.storage.get_statsd_client', return_value=mock_statsd):
            # Apply the metrics decorator to a test function
            from flywheel.storage import measure_latency
            decorated_slow_load = measure_latency("test_operation")(slow_load)

            # Act
            start = time.time()
            decorated_slow_load()
            elapsed = time.time() - start

            # Assert
            # Verify timing was called
            mock_statsd.timing.assert_called_once()

            # Check that the recorded time is approximately the sleep time
            timing_value = mock_statsd.timing.call_args[0][1]
            expected_ms = 100  # 100ms in milliseconds
            # Allow 50ms tolerance
            assert abs(timing_value - expected_ms) < 50, \
                f"Expected timing around {expected_ms}ms, got {timing_value}ms"

    def test_latency_metrics_include_operation_name(self, tmp_path):
        """Test that latency metrics include the operation name in the metric name."""
        # Arrange
        storage_path = tmp_path / "todos.json"
        storage = FileStorage(str(storage_path))

        # Mock statsd client
        mock_statsd = mock.Mock()

        with mock.patch('flywheel.storage.get_statsd_client', return_value=mock_statsd):
            # Act
            storage._load_sync()

            # Assert - verify metric name follows naming convention
            mock_statsd.timing.assert_called()
            metric_name = mock_statsd.timing.call_args[0][0]

            # Metric name should be in format like: storage.operation_name.latency
            assert 'storage' in metric_name.lower() or 'flywheel' in metric_name.lower(), \
                f"Expected metric name to include 'storage' or 'flywheel', got {metric_name}"

    def test_histogram_emitted_for_latency_distribution(self, tmp_path):
        """Test that histogram metrics are emitted for latency distribution."""
        # Arrange
        storage_path = tmp_path / "todos.json"
        storage = FileStorage(str(storage_path))

        # Mock statsd client that supports histogram
        mock_statsd = mock.Mock()
        mock_statsd.histogram = mock.Mock()

        with mock.patch('flywheel.storage.get_statsd_client', return_value=mock_statsd):
            # Act
            storage._load_sync()

            # Assert - check if histogram was called (if statsd client supports it)
            if hasattr(mock_statsd, 'histogram'):
                # If histogram method exists, it should be called
                call_args = mock_statsd.histogram.call_args_list
                # At least one histogram call for load operation
                assert len(call_args) > 0, "Expected histogram metric to be emitted"

    def test_concurrent_operations_metrics_tracked_separately(self, tmp_path):
        """Test that concurrent operations track metrics separately."""
        # Arrange
        storage_path = tmp_path / "todos.json"
        storage = FileStorage(str(storage_path))

        # Mock statsd client
        mock_statsd = mock.Mock()

        async def concurrent_ops():
            tasks = []
            for _ in range(3):
                tasks.append(storage._load())
            await asyncio.gather(*tasks)

        with mock.patch('flywheel.storage.get_statsd_client', return_value=mock_statsd):
            # Act
            asyncio.run(concurrent_ops())

            # Assert - verify metrics were tracked for all operations
            mock_statsd.timing.assert_called()
            call_count = mock_statsd.timing.call_count

            # Should have at least 3 timing calls (one per load operation)
            assert call_count >= 3, f"Expected at least 3 timing calls, got {call_count}"

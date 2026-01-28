"""Tests for slow operation threshold warning (Issue #1023)."""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

from flywheel.storage import FileStorage, measure_latency
from flywheel.todo import Todo


class TestSlowOperationThreshold:
    """Test suite for slow operation threshold warning feature."""

    def test_slow_operation_logs_warning_default_threshold(self, tmp_path, caplog):
        """Test that operations exceeding default threshold (1000ms) log warning."""
        # Arrange
        storage_path = tmp_path / "todos.json"
        storage = FileStorage(str(storage_path))

        # Create a slow function that exceeds threshold
        def slow_operation():
            time.sleep(1.1)  # Sleep for 1.1 seconds (1100ms)

        # Apply the measure_latency decorator
        decorated_slow = measure_latency("test_slow")(slow_operation)

        # Act
        with caplog.at_level("WARNING"):
            decorated_slow()

        # Assert - should have a warning log about slow operation
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert len(warning_logs) > 0, "Expected warning log for slow operation"

        # Check warning message contains operation name and timing info
        warning_message = warning_logs[0].message
        assert "test_slow" in warning_message, f"Expected operation name in warning, got: {warning_message}"
        assert "1100" in warning_message or "1.1" in warning_message or "slow" in warning_message.lower(), \
            f"Expected timing info in warning, got: {warning_message}"

    def test_slow_operation_logs_warning_custom_threshold(self, tmp_path, caplog):
        """Test that operations exceeding custom threshold log warning."""
        # Arrange
        storage_path = tmp_path / "todos.json"
        storage = FileStorage(str(storage_path))

        # Set custom threshold via environment variable
        with mock.patch.dict('os.environ', {'FW_STORAGE_SLOW_LOG_THRESHOLD': '500'}):
            # Create a function that exceeds custom threshold but not default
            def moderately_slow_operation():
                time.sleep(0.6)  # 600ms - exceeds 500ms threshold but not 1000ms

            # Apply the measure_latency decorator
            decorated_slow = measure_latency("test_moderate_slow")(moderately_slow_operation)

            # Act
            with caplog.at_level("WARNING"):
                decorated_slow()

            # Assert - should have warning log due to custom threshold
            warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
            assert len(warning_logs) > 0, "Expected warning log with custom threshold of 500ms"

            warning_message = warning_logs[0].message
            assert "test_moderate_slow" in warning_message, \
                f"Expected operation name in warning, got: {warning_message}"

    def test_fast_operation_no_warning(self, tmp_path, caplog):
        """Test that fast operations do not log warning."""
        # Arrange
        storage_path = tmp_path / "todos.json"

        def fast_operation():
            time.sleep(0.1)  # 100ms - well below threshold

        # Apply the measure_latency decorator
        decorated_fast = measure_latency("test_fast")(fast_operation)

        # Act
        with caplog.at_level("WARNING"):
            decorated_fast()

        # Assert - should NOT have a warning log
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert len(warning_logs) == 0, "Expected no warning log for fast operation"

    def test_slow_async_operation_logs_warning(self, tmp_path, caplog):
        """Test that slow async operations also log warning."""
        # Arrange
        storage_path = tmp_path / "todos.json"
        storage = FileStorage(str(storage_path))

        # Create a slow async function
        async def slow_async_operation():
            await asyncio.sleep(1.1)  # Sleep for 1.1 seconds

        # Apply the measure_latency decorator
        decorated_slow_async = measure_latency("test_slow_async")(slow_async_operation)

        # Act
        with caplog.at_level("WARNING"):
            asyncio.run(decorated_slow_async())

        # Assert - should have a warning log
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert len(warning_logs) > 0, "Expected warning log for slow async operation"

        warning_message = warning_logs[0].message
        assert "test_slow_async" in warning_message, \
            f"Expected operation name in warning, got: {warning_message}"

    def test_threshold_configured_via_environment_variable(self, tmp_path, caplog):
        """Test that threshold can be configured via environment variable."""
        # Arrange
        storage_path = tmp_path / "todos.json"

        # Test with very low threshold
        with mock.patch.dict('os.environ', {'FW_STORAGE_SLOW_LOG_THRESHOLD': '50'}):
            # Function that takes 100ms
            def slow_operation():
                time.sleep(0.1)

            decorated = measure_latency("test_env_threshold")(slow_operation)

            # Act
            with caplog.at_level("WARNING"):
                decorated()

            # Assert - should trigger warning with 50ms threshold
            warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
            assert len(warning_logs) > 0, "Expected warning log with 50ms threshold"

    def test_warning_includes_timing_details(self, tmp_path, caplog):
        """Test that warning log includes detailed timing information."""
        # Arrange
        storage_path = tmp_path / "todos.json"

        def slow_operation():
            time.sleep(1.2)

        decorated = measure_latency("test_timing_details")(slow_operation)

        # Act
        with caplog.at_level("WARNING"):
            decorated()

        # Assert - warning should include timing details
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert len(warning_logs) > 0

        warning_message = warning_logs[0].message
        # Should include milliseconds and operation info
        assert "ms" in warning_message or "millisecond" in warning_message.lower(), \
            f"Expected timing unit in warning, got: {warning_message}"
        assert "test_timing_details" in warning_message, \
            f"Expected operation name, got: {warning_message}"

    def test_invalid_threshold_uses_default(self, tmp_path, caplog):
        """Test that invalid threshold values fall back to default."""
        # Arrange
        storage_path = tmp_path / "todos.json"

        # Test with invalid threshold (non-numeric)
        with mock.patch.dict('os.environ', {'FW_STORAGE_SLOW_LOG_THRESHOLD': 'invalid'}):
            def slow_operation():
                time.sleep(1.1)

            decorated = measure_latency("test_invalid_threshold")(slow_operation)

            # Act - should use default threshold and log warning
            with caplog.at_level("WARNING"):
                decorated()

            # Assert - should still work with default threshold
            warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
            assert len(warning_logs) > 0, "Expected warning log with default threshold when env var is invalid"

    def test_negative_threshold_treated_as_disabled(self, tmp_path, caplog):
        """Test that negative threshold disables slow operation warnings."""
        # Arrange
        storage_path = tmp_path / "todos.json"

        # Test with negative threshold (should disable warnings)
        with mock.patch.dict('os.environ', {'FW_STORAGE_SLOW_LOG_THRESHOLD': '-1'}):
            def slow_operation():
                time.sleep(1.1)

            decorated = measure_latency("test_disabled_warning")(slow_operation)

            # Act
            with caplog.at_level("WARNING"):
                decorated()

            # Assert - should NOT have warning when threshold is negative
            warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
            assert len(warning_logs) == 0, "Expected no warning log when threshold is negative (disabled)"

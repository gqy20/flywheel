"""Tests for performance metrics tracking in JSONFormatter (Issue #1618)."""
import json
import logging
import pytest
from io import StringIO

from src.flywheel.storage import JSONFormatter


class TestPerformanceMetricsTracking:
    """Test that JSONFormatter properly formats performance metrics."""

    def test_json_formatter_includes_duration_ms(self):
        """Test that duration_ms field is included in JSON output."""
        # Create a string handler to capture log output
        logger = logging.getLogger('test_performance')
        logger.setLevel(logging.INFO)

        # Remove any existing handlers
        logger.handlers.clear()

        # Create a string stream and handler with JSONFormatter
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        # Log a message with duration_ms in extra dict
        logger.info("I/O operation completed", extra={'duration_ms': 42.5})

        # Parse the JSON output
        log_output = stream.getvalue().strip()
        log_data = json.loads(log_output)

        # Verify duration_ms is in the output
        assert 'duration_ms' in log_data
        assert log_data['duration_ms'] == 42.5
        assert log_data['message'] == "I/O operation completed"
        assert log_data['level'] == "INFO"

    def test_json_formatter_includes_multiple_performance_metrics(self):
        """Test that multiple performance metrics can be included."""
        logger = logging.getLogger('test_performance_multi')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        # Log with multiple performance metrics
        logger.info(
            "Lock acquired",
            extra={
                'duration_ms': 15.3,
                'lock_wait_ms': 8.2,
                'operation': 'load_cache'
            }
        )

        log_output = stream.getvalue().strip()
        log_data = json.loads(log_output)

        # Verify all metrics are present
        assert log_data['duration_ms'] == 15.3
        assert log_data['lock_wait_ms'] == 8.2
        assert log_data['operation'] == 'load_cache'
        assert log_data['message'] == "Lock acquired"

    def test_json_formatter_without_performance_metrics(self):
        """Test that formatter works without performance metrics."""
        logger = logging.getLogger('test_performance_none')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        # Log without any extra fields
        logger.info("Simple log message")

        log_output = stream.getvalue().strip()
        log_data = json.loads(log_output)

        # Verify basic fields are present but duration_ms is not
        assert log_data['message'] == "Simple log message"
        assert log_data['level'] == "INFO"
        assert 'duration_ms' not in log_data

    def test_json_formatter_with_zero_duration(self):
        """Test that zero duration is properly handled."""
        logger = logging.getLogger('test_performance_zero')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        # Log with zero duration
        logger.info("Fast operation", extra={'duration_ms': 0.0})

        log_output = stream.getvalue().strip()
        log_data = json.loads(log_output)

        assert log_data['duration_ms'] == 0.0
        assert log_data['message'] == "Fast operation"

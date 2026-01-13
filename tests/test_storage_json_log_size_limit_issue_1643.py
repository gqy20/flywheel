"""Test JSON log data size limit (Issue #1643).

This test verifies that:
1. JSONFormatter truncates string values that exceed MAX_LOG_SIZE
2. Truncated strings have '...[truncated]' suffix
3. The size limit helps prevent log parser issues and high ingestion costs
"""

import json
import logging
from io import StringIO

import pytest

from flywheel.storage import JSONFormatter


class TestJSONLogSizeLimit:
    """Test JSON log data size limit (Issue #1643)."""

    def test_jsonformatter_has_max_log_size_constant(self):
        """Test that JSONFormatter has a MAX_LOG_SIZE constant."""
        assert hasattr(JSONFormatter, 'MAX_LOG_SIZE'), \
            "JSONFormatter should have a MAX_LOG_SIZE constant"
        assert isinstance(JSONFormatter.MAX_LOG_SIZE, int), \
            "MAX_LOG_SIZE should be an integer"
        assert JSONFormatter.MAX_LOG_SIZE > 0, \
            "MAX_LOG_SIZE should be positive"

    def test_jsonformatter_truncates_large_string_values(self):
        """Test that JSONFormatter truncates string values that exceed MAX_LOG_SIZE."""
        formatter = JSONFormatter()

        # Create a log record with a very large string value
        large_string = "x" * 20000  # 20KB string
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None,
        )
        # Add a custom field with large string
        record.large_data = large_string

        # Format the record
        formatted_output = formatter.format(record)
        log_data = json.loads(formatted_output)

        # Check that large_data is truncated
        assert 'large_data' in log_data, "large_data field should be present"
        large_data_value = log_data['large_data']
        assert isinstance(large_data_value, str), "large_data should be a string"

        # Check that the value is truncated with suffix
        assert len(large_data_value) <= JSONFormatter.MAX_LOG_SIZE, \
            f"Truncated value should not exceed MAX_LOG_SIZE ({JSONFormatter.MAX_LOG_SIZE} bytes)"
        assert large_data_value.endswith('...[truncated]'), \
            "Truncated string should end with '...[truncated]' suffix"

    def test_jsonformatter_truncates_multiple_large_fields(self):
        """Test that JSONFormatter truncates multiple large fields independently."""
        formatter = JSONFormatter()

        # Create a log record with multiple large strings
        large_string_1 = "a" * 15000  # 15KB
        large_string_2 = "b" * 18000  # 18KB

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None,
        )
        record.data_1 = large_string_1
        record.data_2 = large_string_2

        # Format the record
        formatted_output = formatter.format(record)
        log_data = json.loads(formatted_output)

        # Check that both fields are truncated
        assert 'data_1' in log_data
        assert 'data_2' in log_data

        assert len(log_data['data_1']) <= JSONFormatter.MAX_LOG_SIZE
        assert len(log_data['data_2']) <= JSONFormatter.MAX_LOG_SIZE

        assert log_data['data_1'].endswith('...[truncated]')
        assert log_data['data_2'].endswith('...[truncated]')

    def test_jsonformatter_does_not_truncate_small_strings(self):
        """Test that JSONFormatter does not truncate small strings."""
        formatter = JSONFormatter()

        # Create a log record with small strings
        small_string = "Small data"
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None,
        )
        record.small_data = small_string

        # Format the record
        formatted_output = formatter.format(record)
        log_data = json.loads(formatted_output)

        # Check that small string is not truncated
        assert log_data['small_data'] == small_string, \
            "Small strings should not be truncated"
        assert not log_data['small_data'].endswith('...[truncated]'), \
            "Small strings should not have truncation suffix"

    def test_jsonformatter_handles_non_string_values(self):
        """Test that JSONFormatter handles non-string values correctly."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None,
        )
        record.number = 42
        record.boolean = True
        record.none_value = None
        record.list_data = [1, 2, 3]

        # Format the record
        formatted_output = formatter.format(record)
        log_data = json.loads(formatted_output)

        # Non-string values should be preserved as-is
        assert log_data['number'] == 42
        assert log_data['boolean'] == True
        assert log_data['none_value'] == None
        assert log_data['list_data'] == [1, 2, 3]

    def test_jsonformatter_truncates_nested_string_values(self):
        """Test that JSONFormatter truncates strings in nested structures."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None,
        )
        # Add a nested structure with large strings
        large_string = "y" * 20000
        record.nested = {"key": large_string, "other": "value"}

        # Format the record
        formatted_output = formatter.format(record)
        log_data = json.loads(formatted_output)

        # Check that nested string is truncated
        assert 'nested' in log_data
        assert isinstance(log_data['nested'], dict)
        assert 'key' in log_data['nested']
        assert len(log_data['nested']['key']) <= JSONFormatter.MAX_LOG_SIZE
        assert log_data['nested']['key'].endswith('...[truncated]')

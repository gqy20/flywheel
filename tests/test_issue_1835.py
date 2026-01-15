"""Test for Issue #1835 - JSONFormatter.format method should return JSON string"""
import json
import logging
import pytest
from flywheel.storage import JSONFormatter


def test_json_formatter_returns_string():
    """Test that JSONFormatter.format returns a valid JSON string, not None."""
    formatter = JSONFormatter()

    # Create a log record
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None,
    )

    # Format the record
    result = formatter.format(record)

    # Assert that result is not None (this would fail if return statement is missing)
    assert result is not None, "JSONFormatter.format should not return None"

    # Assert that result is a valid JSON string
    assert isinstance(result, str), "JSONFormatter.format should return a string"

    # Assert that the result can be parsed as JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict), "Result should be a JSON object"

    # Verify expected fields are present
    assert 'timestamp' in parsed
    assert 'level' in parsed
    assert 'logger' in parsed
    assert 'message' in parsed
    assert parsed['message'] == 'Test message'


def test_json_formatter_with_extra_fields():
    """Test that JSONFormatter.format handles extra fields correctly."""
    formatter = JSONFormatter()

    # Create a log record with extra fields
    record = logging.LogRecord(
        name='test_logger',
        level=logging.WARNING,
        pathname='test.py',
        lineno=42,
        msg='Warning message',
        args=(),
        exc_info=None,
    )
    # Add custom extra fields
    record.custom_field = 'custom_value'
    record.user_id = 12345

    # Format the record
    result = formatter.format(record)

    # Assert that result is not None and is valid JSON
    assert result is not None, "JSONFormatter.format should not return None"
    assert isinstance(result, str), "JSONFormatter.format should return a string"

    # Parse and verify extra fields are included
    parsed = json.loads(result)
    assert 'custom_field' in parsed
    assert parsed['custom_field'] == 'custom_value'
    assert 'user_id' in parsed
    assert parsed['user_id'] == 12345

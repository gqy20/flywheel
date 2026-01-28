"""Test for Issue #1809 - JSONFormatter.format method should return JSON string."""

import logging
import json
from flywheel.storage import JSONFormatter


def test_jsonformatter_returns_json_string():
    """Test that JSONFormatter.format returns a valid JSON string.

    This test verifies the fix for Issue #1809 which claimed that the
    JSONFormatter.format method did not return any value.

    The method should return a JSON string containing all log fields.
    """
    # Create a JSON formatter instance
    formatter = JSONFormatter()

    # Create a log record
    record = logging.LogRecord(
        name='test.logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None,
    )

    # Call format method
    result = formatter.format(record)

    # Assert that format returns a string (not None)
    assert result is not None, "JSONFormatter.format should not return None"

    # Assert that the result is a string
    assert isinstance(result, str), "JSONFormatter.format should return a string"

    # Assert that the result is valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict), "Result should be a valid JSON object"

    # Assert that standard fields are present
    assert 'timestamp' in parsed, "JSON should contain timestamp field"
    assert 'level' in parsed, "JSON should contain level field"
    assert 'logger' in parsed, "JSON should contain logger field"
    assert 'message' in parsed, "JSON should contain message field"
    assert 'thread_id' in parsed, "JSON should contain thread_id field (Issue #1797)"

    # Assert field values are correct
    assert parsed['level'] == 'INFO', "Level should be INFO"
    assert parsed['logger'] == 'test.logger', "Logger name should match"
    assert parsed['message'] == 'Test message', "Message should match"


def test_jsonformatter_with_custom_fields():
    """Test that JSONFormatter.format includes custom extra fields."""
    formatter = JSONFormatter()

    # Create a log record with custom extra fields
    record = logging.LogRecord(
        name='test.logger',
        level=logging.ERROR,
        pathname='test.py',
        lineno=42,
        msg='Error occurred',
        args=(),
        exc_info=None,
    )

    # Add custom extra fields
    record.custom_field = 'custom_value'
    record.user_id = 12345

    result = formatter.format(record)

    # Assert result is not None and is valid JSON
    assert result is not None, "JSONFormatter.format should not return None"
    parsed = json.loads(result)

    # Assert custom fields are included
    assert parsed.get('custom_field') == 'custom_value', "Custom field should be included"
    assert parsed.get('user_id') == 12345, "Custom numeric field should be included"


def test_jsonformatter_with_exception():
    """Test that JSONFormatter.format handles exception info correctly."""
    formatter = JSONFormatter()

    # Create a log record with exception info
    try:
        raise ValueError("Test exception")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name='test.logger',
        level=logging.ERROR,
        pathname='test.py',
        lineno=42,
        msg='Exception occurred',
        args=(),
        exc_info=exc_info,
    )

    result = formatter.format(record)

    # Assert result is not None and is valid JSON
    assert result is not None, "JSONFormatter.format should not return None with exception"
    parsed = json.loads(result)

    # Assert exception field is present
    assert 'exception' in parsed, "Exception should be included in JSON"
    assert 'ValueError' in parsed['exception'], "Exception type should be in traceback"

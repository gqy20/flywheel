"""Tests for Issue #1760 - Verify JSONFormatter.format implementation is complete.

This test verifies that:
1. JSONFormatter.format method is fully implemented
2. The format method properly handles redaction logic
3. The format method returns valid JSON output
"""

import logging
import json
from flywheel.storage import JSONFormatter


def test_jsonformatter_format_is_complete():
    """Test that JSONFormatter.format is fully implemented and returns valid JSON."""
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

    # Assert that result is a string
    assert isinstance(result, str), "format() should return a string"

    # Assert that result is valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict), "format() should return valid JSON dict"

    # Assert basic fields exist
    assert 'message' in parsed
    assert parsed['message'] == 'Test message'


def test_jsonformatter_format_with_redaction():
    """Test that JSONFormatter.format properly redacts sensitive fields."""
    formatter = JSONFormatter()

    # Create a log record with sensitive data
    record = logging.LogRecord(
        name='test.logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=42,
        msg='Test with password',
        args=(),
        exc_info=None,
    )
    record.password = 'secret123'  # Sensitive field
    record.api_key = 'key-xyz-789'  # Sensitive field
    record.normal_field = 'public_value'

    # Call format method
    result = formatter.format(record)

    # Parse JSON output
    parsed = json.loads(result)

    # Verify sensitive fields are redacted
    assert 'password' in parsed
    assert parsed['password'] == '***REDACTED***', "password should be redacted"

    assert 'api_key' in parsed
    assert parsed['api_key'] == '***REDACTED***', "api_key should be redacted"

    # Verify normal field is not redacted
    assert 'normal_field' in parsed
    assert parsed['normal_field'] == 'public_value', "normal field should not be redacted"


def test_jsonformatter_format_with_large_json_truncation():
    """Test that JSONFormatter.format properly handles JSON size truncation."""
    formatter = JSONFormatter()

    # Create a log record with a very large message
    large_message = 'x' * 100000  # 100KB message
    record = logging.LogRecord(
        name='test.logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=42,
        msg=large_message,
        args=(),
        exc_info=None,
    )

    # Call format method
    result = formatter.format(record)

    # Verify result is valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict)

    # Verify JSON size is within limits
    assert len(result) <= formatter.MAX_JSON_SIZE, "JSON output should be truncated to MAX_JSON_SIZE"

    # Verify message was truncated
    assert 'message' in parsed
    assert len(parsed['message']) < len(large_message), "message should be truncated"
    assert 'truncated' in parsed['message'].lower() or len(parsed['message']) < len(large_message)


def test_jsonformatter_format_with_exception():
    """Test that JSONFormatter.format properly handles exception info."""
    formatter = JSONFormatter()

    # Create a log record with exception info
    try:
        raise ValueError("Test exception")
    except ValueError:
        exc_info = True
        record = logging.LogRecord(
            name='test.logger',
            level=logging.ERROR,
            pathname='test.py',
            lineno=42,
            msg='Error occurred',
            args=(),
            exc_info=exc_info,
        )

    # Call format method
    result = formatter.format(record)

    # Verify result is valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict)

    # Verify exception field exists
    assert 'exception' in parsed
    assert isinstance(parsed['exception'], str)
    assert 'ValueError' in parsed['exception']
    assert 'Test exception' in parsed['exception']

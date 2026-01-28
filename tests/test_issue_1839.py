"""Test for Issue #1839 - JSONFormatter.format method should return JSON string

This test verifies that the AI scanner report was a false positive.
The JSONFormatter.format method does have a return statement at line 390.
"""
import json
import logging
import pytest
from flywheel.storage import JSONFormatter


def test_json_formatter_returns_string():
    """Test that JSONFormatter.format returns a valid JSON string."""
    formatter = JSONFormatter()

    # Create a log record
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message',
        args=(),
        exc_info=None
    )

    # Call format method
    result = formatter.format(record)

    # Verify result is a string
    assert isinstance(result, str), f"Expected str, got {type(result)}"

    # Verify result is valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict)

    # Verify standard fields are present
    assert 'timestamp' in parsed
    assert 'level' in parsed
    assert 'logger' in parsed
    assert 'message' in parsed

    # Verify values
    assert parsed['level'] == 'INFO'
    assert parsed['logger'] == 'test_logger'
    assert parsed['message'] == 'Test message'


def test_json_formatter_with_custom_fields():
    """Test that JSONFormatter.format handles custom fields correctly."""
    formatter = JSONFormatter()

    # Create a log record with extra fields
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message',
        args=(),
        exc_info=None
    )

    # Add custom fields
    record.user_id = '12345'
    record.request_id = 'abc-123'

    # Call format method
    result = formatter.format(record)

    # Verify result is valid JSON
    parsed = json.loads(result)

    # Verify custom fields are present
    assert 'user_id' in parsed
    assert parsed['user_id'] == '12345'
    assert 'request_id' in parsed
    assert parsed['request_id'] == 'abc-123'


def test_json_formatter_with_sensitive_data():
    """Test that JSONFormatter.format redacts sensitive fields."""
    formatter = JSONFormatter()

    # Create a log record with sensitive data
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message',
        args=(),
        exc_info=None
    )

    # Add sensitive fields
    record.password = 'secret123'
    record.api_key = 'key-xyz-789'

    # Call format method
    result = formatter.format(record)

    # Verify result is valid JSON
    parsed = json.loads(result)

    # Verify sensitive fields are redacted
    assert 'password' in parsed
    assert parsed['password'] == '***REDACTED***'
    assert 'api_key' in parsed
    assert parsed['api_key'] == '***REDACTED***'

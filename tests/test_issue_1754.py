"""Test for Issue #1754 - JSONFormatter.format method completeness.

This test verifies that the JSONFormatter.format method is complete and handles:
1. Sensitive field redaction (Issue #1633)
2. Large value truncation (Issue #1643)
3. JSON serialization errors (Issue #1646)
4. Final JSON size check (Issue #1722)
"""

import json
import logging
from io import StringIO
from flywheel.storage import JSONFormatter


def test_json_formatter_complete():
    """Test that JSONFormatter.format method is complete and returns valid JSON."""
    formatter = JSONFormatter()

    # Create a log record with various fields
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None,
    )

    # Add some custom fields
    record.user_id = '12345'
    record.request_id = 'abc-def'

    # Format the record
    output = formatter.format(record)

    # Verify output is valid JSON
    assert output is not None, "format() should return a value"
    assert isinstance(output, str), "format() should return a string"

    # Parse the JSON to verify it's valid
    parsed = json.loads(output)

    # Verify standard fields are present
    assert 'timestamp' in parsed, "JSON should contain timestamp"
    assert 'level' in parsed, "JSON should contain level"
    assert 'logger' in parsed, "JSON should contain logger"
    assert 'message' in parsed, "JSON should contain message"

    # Verify custom fields are present
    assert 'user_id' in parsed, "JSON should contain custom user_id field"
    assert 'request_id' in parsed, "JSON should contain custom request_id field"


def test_json_formatter_sensitive_fields_redacted():
    """Test that sensitive fields are properly redacted (Issue #1633)."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=42,
        msg='Login attempt',
        args=(),
        exc_info=None,
    )

    # Add sensitive fields
    record.password = 'secret123'
    record.api_key = 'key-abc-123'
    record.token = 'token-xyz-789'

    # Format the record
    output = formatter.format(record)

    # Parse the JSON
    parsed = json.loads(output)

    # Verify sensitive fields are redacted
    assert parsed['password'] == '***REDACTED***', "password should be redacted"
    assert parsed['api_key'] == '***REDACTED***', "api_key should be redacted"
    assert parsed['token'] == '***REDACTED***', "token should be redacted"


def test_json_formatter_truncates_large_values():
    """Test that large string values are truncated (Issue #1643)."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None,
    )

    # Add a very large string (larger than MAX_LOG_SIZE)
    large_data = 'x' * (formatter.MAX_LOG_SIZE + 1000)
    record.large_field = large_data

    # Format the record
    output = formatter.format(record)

    # Parse the JSON
    parsed = json.loads(output)

    # Verify the large field was truncated
    assert len(parsed['large_field']) <= formatter.MAX_LOG_SIZE, \
        f"Large field should be truncated to MAX_LOG_SIZE ({formatter.MAX_LOG_SIZE} bytes)"


def test_json_formatter_handles_non_serializable():
    """Test that non-serializable objects are handled (Issue #1646)."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None,
    )

    # Add a non-serializable object
    class CustomObject:
        def __str__(self):
            return "CustomObject()"

    record.custom_obj = CustomObject()

    # Format the record - should not raise an exception
    output = formatter.format(record)

    # Verify output is valid JSON
    parsed = json.loads(output)
    assert 'custom_obj' in parsed, "Custom object should be in output"


def test_json_formatter_respects_max_json_size():
    """Test that final JSON size is limited (Issue #1722)."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None,
    )

    # Add many large fields to exceed MAX_JSON_SIZE
    for i in range(100):
        large_value = 'x' * 10000
        setattr(record, f'field_{i}', large_value)

    # Format the record
    output = formatter.format(record)

    # Verify the final JSON size is within limits
    assert len(output) <= formatter.MAX_JSON_SIZE, \
        f"Final JSON should not exceed MAX_JSON_SIZE ({formatter.MAX_JSON_SIZE} bytes)"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

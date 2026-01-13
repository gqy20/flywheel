"""Tests for Issue #1654 - JSON output validity and completeness.

This test ensures that:
1. JSON output is always valid and parseable
2. Sensitive field redaction produces valid JSON strings
3. Truncated values don't break JSON serialization
4. All methods complete properly without truncation
"""
import json
import logging
from flywheel.storage import JSONFormatter


def test_json_output_is_valid():
    """Test that JSON output is always valid and parseable."""
    formatter = JSONFormatter()

    # Create a log record with various field types
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message with "quotes" and {special} chars',
        args=(),
        exc_info=None
    )

    output = formatter.format(record)

    # Should be valid JSON
    try:
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Output is not valid JSON: {e}")


def test_redaction_produces_valid_json():
    """Test that redacted sensitive fields produce valid JSON."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message',
        args=(),
        exc_info=None
    )

    # Add sensitive fields with special characters that could break JSON
    record.password = 'secret"value"with"quotes'
    record.token = 'token\nwith\nnewlines'
    record.api_key = 'key\twith\ttabs'

    output = formatter.format(record)

    # Should be valid JSON
    try:
        parsed = json.loads(output)
        # Check that sensitive fields are redacted
        assert 'password' in parsed
        assert 'token' in parsed
        assert 'api_key' in parsed
        # Redacted values should not contain the original sensitive data
        assert 'secret"value"with"quotes' not in parsed['password']
        assert 'token\nwith\nnewlines' not in parsed['token']
    except json.JSONDecodeError as e:
        raise AssertionError(f"Redacted output is not valid JSON: {e}")


def test_truncation_produces_valid_json():
    """Test that truncated values produce valid JSON."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message',
        args=(),
        exc_info=None
    )

    # Create a value larger than MAX_LOG_SIZE (10KB)
    large_value = "x" * (11 * 1024)
    record.large_field = large_value

    output = formatter.format(record)

    # Should be valid JSON
    try:
        parsed = json.loads(output)
        assert 'large_field' in parsed
        # Should be truncated
        assert len(parsed['large_field']) < len(large_value)
        assert '...[truncated]' in parsed['large_field']
    except json.JSONDecodeError as e:
        raise AssertionError(f"Truncated output is not valid JSON: {e}")


def test_methods_complete_fully():
    """Test that all formatting methods complete without early return."""
    formatter = JSONFormatter()

    # Test _redact_sensitive_fields returns a complete dict
    log_data = {
        'message': 'test',
        'password': 'secret123',
        'token': 'abc',
        'normal_field': 'value'
    }

    redacted = formatter._redact_sensitive_fields(log_data)
    assert isinstance(redacted, dict)
    assert 'message' in redacted
    assert 'password' in redacted
    assert 'token' in redacted
    assert 'normal_field' in redacted
    assert redacted['message'] == 'test'
    assert redacted['normal_field'] == 'value'

    # Test _truncate_large_values returns a complete dict
    large_data = {
        'small': 'test',
        'large': 'x' * (11 * 1024),
        'nested': {'value': 'y' * (11 * 1024)}
    }

    truncated = formatter._truncate_large_values(large_data)
    assert isinstance(truncated, dict)
    assert 'small' in truncated
    assert 'large' in truncated
    assert 'nested' in truncated
    assert len(truncated['large']) < len(large_data['large'])


def test_combined_redaction_and_truncation():
    """Test that redaction and truncation work together without breaking JSON."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message',
        args=(),
        exc_info=None
    )

    # Add both sensitive and large fields
    record.password = 'x' * (11 * 1024)  # Large sensitive value
    record.message = 'y' * (11 * 1024)  # Large normal value
    record.token = 'abc'  # Small sensitive value

    output = formatter.format(record)

    # Should be valid JSON
    try:
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
        # All fields should be present
        assert 'password' in parsed
        assert 'message' in parsed
        assert 'token' in parsed
    except json.JSONDecodeError as e:
        raise AssertionError(f"Combined output is not valid JSON: {e}")

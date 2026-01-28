"""Test for Issue #1780 - Missing Return Statement

This test verifies that JSONFormatter.format() method returns the formatted
JSON string as expected.
"""

import json
import logging
import pytest

from flywheel.storage import JSONFormatter


def test_json_formatter_returns_string():
    """Test that JSONFormatter.format() returns a string."""
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
    assert isinstance(result, str), f"Expected str, got {type(result).__name__}"

    # Assert that result is valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict)

    # Assert that basic fields are present
    assert parsed['level'] == 'INFO'
    assert parsed['logger'] == 'test.logger'
    assert parsed['message'] == 'Test message'


def test_json_formatter_with_custom_fields():
    """Test that JSONFormatter.format() handles custom fields correctly."""
    formatter = JSONFormatter()

    # Create a log record with custom fields
    record = logging.LogRecord(
        name='test.logger',
        level=logging.ERROR,
        pathname='test.py',
        lineno=42,
        msg='Error message',
        args=(),
        exc_info=None,
    )
    # Add custom fields
    record.custom_field = 'custom_value'
    record.user_id = 12345

    # Call format method
    result = formatter.format(record)

    # Assert that result is returned
    assert result is not None
    assert isinstance(result, str)

    # Parse and verify custom fields are included
    parsed = json.loads(result)
    assert parsed['custom_field'] == 'custom_value'
    assert parsed['user_id'] == 12345


def test_json_formatter_returns_non_empty():
    """Test that JSONFormatter.format() returns non-empty string."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name='test',
        level=logging.WARNING,
        pathname='test.py',
        lineno=1,
        msg='Warning',
        args=(),
        exc_info=None,
    )

    result = formatter.format(record)

    # Result should be a non-empty string
    assert isinstance(result, str)
    assert len(result) > 0

    # Should be valid JSON
    parsed = json.loads(result)
    assert len(parsed) > 0

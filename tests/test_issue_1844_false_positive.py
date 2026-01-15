"""Test for Issue #1844 - False Positive Verification

This test verifies that Issue #1844 is a false positive.
The issue claims that JSONFormatter.format() lacks a return statement,
but the method actually has a complete implementation with proper return.

Issue #1844: [Bug] JSONFormatter.format() 方法缺少返回语句
Status: FALSE POSITIVE - The method correctly returns json_output at line 390
"""

import logging
import json
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from flywheel.storage import JSONFormatter


def test_jsonformatter_has_return_statement():
    """Verify that JSONFormatter.format() properly returns a JSON string.

    This test disproves Issue #1844 which claims the method lacks a return statement.
    """
    formatter = JSONFormatter()

    # Create a basic log record
    record = logging.LogRecord(
        name='test.logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None
    )

    # Call format() - it should return a string, not None
    result = formatter.format(record)

    # Verify the result is not None (which would happen if there was no return)
    assert result is not None, "format() returned None - missing return statement?"

    # Verify the result is a string
    assert isinstance(result, str), f"format() should return str, got {type(result)}"

    # Verify the result is valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict), "JSON should parse to a dict"

    # Verify expected fields are present
    assert 'timestamp' in parsed, "Missing timestamp field"
    assert 'level' in parsed, "Missing level field"
    assert 'logger' in parsed, "Missing logger field"
    assert 'message' in parsed, "Missing message field"
    assert parsed['message'] == 'Test message', "Message content mismatch"

    print("✓ JSONFormatter.format() correctly returns JSON string")
    print(f"✓ Issue #1844 is FALSE POSITIVE - method has return statement at line 390")


def test_jsonformatter_with_custom_fields():
    """Test JSONFormatter with custom extra fields."""
    formatter = JSONFormatter()

    # Create log record with extra fields
    record = logging.LogRecord(
        name='test.app',
        level=logging.WARNING,
        pathname='app.py',
        lineno=100,
        msg='Warning with custom data',
        args=(),
        exc_info=None
    )
    # Add custom fields
    record.custom_field = 'custom_value'
    record.user_id = 12345

    result = formatter.format(record)

    # Verify result is not None and is valid JSON
    assert result is not None, "format() returned None"
    parsed = json.loads(result)
    assert parsed['custom_field'] == 'custom_value'
    assert parsed['user_id'] == 12345
    assert parsed['level'] == 'WARNING'

    print("✓ JSONFormatter handles custom fields correctly")


def test_jsonformatter_with_exception():
    """Test JSONFormatter with exception info."""
    formatter = JSONFormatter()

    try:
        raise ValueError("Test exception")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name='test.error',
        level=logging.ERROR,
        pathname='error.py',
        lineno=1,
        msg='Error occurred',
        args=(),
        exc_info=exc_info
    )

    result = formatter.format(record)

    # Verify result is not None and contains exception info
    assert result is not None, "format() returned None"
    parsed = json.loads(result)
    assert 'exception' in parsed, "Missing exception field"
    assert 'ValueError' in parsed['exception'], "Exception type not in output"
    assert 'Test exception' in parsed['exception'], "Exception message not in output"

    print("✓ JSONFormatter handles exceptions correctly")


if __name__ == '__main__':
    # Run tests manually
    test_jsonformatter_has_return_statement()
    test_jsonformatter_with_custom_fields()
    test_jsonformatter_with_exception()
    print("\n" + "="*70)
    print("All tests passed! Issue #1844 is confirmed as FALSE POSITIVE")
    print("="*70)

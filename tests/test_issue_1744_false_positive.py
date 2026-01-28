"""Test to verify Issue #1744 is a false positive.

Issue #1744 claimed that json_output variable was incomplete and function
lacked return statement, but the code is actually complete and working correctly.
"""

import json
import logging
from flywheel.storage import JSONFormatter


def test_jsonformatter_complete_implementation():
    """Verify that JSONFormatter.format() properly returns JSON output.

    This test verifies that:
    1. json_output variable is properly assigned
    2. The function has a return statement
    3. The function returns valid JSON in all cases

    Issue #1744 is a FALSE POSITIVE - the code is complete.
    """
    formatter = JSONFormatter()

    # Create a log record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )

    # Format the record
    result = formatter.format(record)

    # Verify the result is a valid JSON string
    assert result is not None, "format() should return a value"
    assert isinstance(result, str), "format() should return a string"

    # Verify it's valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict), "Result should parse to a dict"
    assert 'message' in parsed, "Result should contain 'message' field"
    assert parsed['message'] == "Test message"


def test_jsonformatter_with_non_serializable_data():
    """Verify JSONFormatter handles non-serializable objects correctly.

    This tests the fallback to _make_serializable() when json.dumps() fails.
    """
    formatter = JSONFormatter()

    # Create a log record with non-serializable object
    class CustomClass:
        def __str__(self):
            return "CustomClass instance"

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )

    # Add custom field with non-serializable object
    record.custom = CustomClass()

    # Format the record - should not crash
    result = formatter.format(record)

    # Verify the result is valid JSON
    assert result is not None, "format() should return a value"
    assert isinstance(result, str), "format() should return a string"

    # Verify it's valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_jsonformatter_with_large_json():
    """Verify JSONFormatter handles large JSON correctly (Issue #1722).

    This tests that json_output is properly reassigned when truncating
    large JSON to fit MAX_JSON_SIZE.
    """
    formatter = JSONFormatter()

    # Create a log record with a very large message
    large_message = "x" * 10000  # Much larger than MAX_JSON_SIZE
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg=large_message,
        args=(),
        exc_info=None
    )

    # Format the record
    result = formatter.format(record)

    # Verify the result is valid JSON and truncated
    assert result is not None, "format() should return a value"
    assert isinstance(result, str), "format() should return a string"

    # Verify it's valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict)
    assert 'message' in parsed

    # Verify the message was truncated
    assert len(parsed['message']) < len(large_message)
    assert 'truncated' in parsed['message'].lower() or len(result) <= formatter.MAX_JSON_SIZE


def test_jsonformatter_return_statement_exists():
    """Direct verification that format() method has return statement.

    This is a direct test to disprove Issue #1744's claim that
    the function lacks a return statement.
    """
    import inspect
    from flywheel.storage import JSONFormatter

    formatter = JSONFormatter()

    # Get the source code of the format method
    source = inspect.getsource(formatter.format)

    # Verify return statement exists in the source
    assert 'return' in source, "format() method should have a return statement"
    assert 'return json_output' in source, "format() should return json_output"

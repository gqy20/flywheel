"""Test for Issue #1734 - Verify JSON serialization error handling is correct.

Issue #1734 was a false positive - the AI scanner incorrectly reported that
json_output was undefined when JSON serialization fails. The actual code
correctly handles both cases:

1. Initial serialization failure (line 257-262)
2. Re-serialization failure after message truncation (line 277-281)

Both cases properly assign json_output = json.dumps(safe_log_data)
"""

import json
import logging
from flywheel.storage import JSONFormatter


class NonSerializable:
    """A custom class that cannot be JSON serialized."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f"NonSerializable({self.value})"


def test_json_serialization_error_handling_primary():
    """Test that primary JSON serialization error is handled correctly.

    This verifies the code path at lines 257-262 in storage.py.
    When json.dumps(log_data) fails, the code should:
    1. Call _make_serializable to convert values to safe strings
    2. Call json.dumps again with the safe data
    3. Return the result (json_output is always defined)
    """
    formatter = JSONFormatter()

    # Create a log record with non-serializable data
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message with non-serializable object",
        args=(),
        exc_info=None,
    )

    # Add non-serializable extra data
    # We can't add it via extra= since logging validates that,
    # so we'll modify the formatter's behavior by testing format directly
    # The formatter internally uses extra fields from record.__dict__

    # Create a mock scenario where we have non-serializable data
    # by adding it to the record after creation
    custom_object = NonSerializable("test_value")
    record.custom_field = custom_object

    # This should not raise an error and should return valid JSON
    result = formatter.format(record)

    # Verify the result is a valid JSON string
    assert isinstance(result, str)
    assert len(result) > 0

    # Verify it can be parsed as JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict)

    # The non-serializable object should be converted to its string representation
    assert 'custom_field' in parsed
    assert str(custom_object) in parsed['custom_field']


def test_json_serialization_error_handling_after_truncation():
    """Test that JSON serialization error after truncation is handled correctly.

    This verifies the code path at lines 277-281 in storage.py.
    After message truncation, if json.dumps(log_data) fails again,
    the code should use _make_serializable and assign json_output.
    """
    formatter = JSONFormatter()

    # Create a log record with a very large message
    # and non-serializable data that will cause the second json.dumps to fail
    large_message = "x" * (2 * 1024 * 1024)  # 2MB message (exceeds MAX_JSON_SIZE)

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg=large_message,
        args=(),
        exc_info=None,
    )

    # Add non-serializable object that will cause serialization to fail
    # even after truncation
    record.non_serializable = NonSerializable("complex_object")

    # This should not raise an error
    # The code will:
    # 1. Try to serialize (might succeed or fail depending on data)
    # 2. If JSON is too large, truncate message
    # 3. Try to re-serialize (might fail if non-serializable objects remain)
    # 4. If re-serialization fails, use _make_serializable
    result = formatter.format(record)

    # Verify we got valid JSON output
    assert isinstance(result, str)
    assert len(result) > 0

    # Verify it can be parsed
    parsed = json.loads(result)
    assert isinstance(parsed, dict)

    # The message should be truncated
    assert 'message' in parsed
    assert len(parsed['message']) < len(large_message)


def test_multiple_non_serializable_fields():
    """Test handling multiple non-serializable fields in log data."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test with multiple non-serializable objects",
        args=(),
        exc_info=None,
    )

    # Add multiple non-serializable fields
    record.obj1 = NonSerializable("first")
    record.obj2 = NonSerializable("second")
    record.obj3 = lambda x: x * 2  # Lambda functions aren't serializable

    result = formatter.format(record)

    # Verify valid JSON
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)

    # All non-serializable objects should be converted to strings
    assert 'obj1' in parsed
    assert 'obj2' in parsed
    assert 'obj3' in parsed


def test_nested_non_serializable_structures():
    """Test handling nested structures with non-serializable values."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test with nested non-serializable data",
        args=(),
        exc_info=None,
    )

    # Add nested data with non-serializable objects
    record.nested = {
        'level1': {
            'level2': {
                'obj': NonSerializable("deeply_nested")
            },
            'another_obj': lambda: "test"
        }
    }

    result = formatter.format(record)

    # Verify valid JSON
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)

    # Nested structure should be preserved with string-converted values
    assert 'nested' in parsed
    assert isinstance(parsed['nested'], dict)


def test_json_output_always_defined():
    """Test that json_output is always defined and returned.

    This is the core assertion for Issue #1734 - verifying that
    json_output is never undefined when the format method returns.
    """
    formatter = JSONFormatter()

    # Create various test cases that could potentially fail
    test_cases = [
        ("Simple message", {"key": "value"}),
        ("With non-serializable", {"obj": NonSerializable("test")}),
        ("With lambda", {"func": lambda x: x}),
        ("Large message", "x" * 5_000_000),  # Very large message
    ]

    for msg, extra in test_cases:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=(),
            exc_info=None,
        )

        # Add extra fields if they're a dict
        if isinstance(extra, dict):
            for key, value in extra.items():
                setattr(record, key, value)
        else:
            record.message = extra

        # This should always return a valid string
        result = formatter.format(record)

        # Verify result is defined and is valid JSON
        assert result is not None, f"json_output was undefined for: {msg}"
        assert isinstance(result, str), f"Result is not a string for: {msg}"
        assert len(result) > 0, f"Result is empty for: {msg}"

        # Verify it's valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict), f"Result is not a valid JSON object for: {msg}"

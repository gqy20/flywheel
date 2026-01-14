"""
Test to verify Issue #1740 is a false positive.

The issue claimed there was an incomplete variable assignment at line 239,
but the actual code shows complete JSON serialization logic at lines 257-262.
"""

import json
import logging
from flywheel.storage import JSONStorageHandler


def test_json_serialization_complete():
    """Verify that JSON serialization is complete and working."""
    handler = JSONStorageHandler()

    # Create a log record
    logger = logging.getLogger('test_issue_1740')
    record = logger.makeRecord(
        name='test',
        level=logging.INFO,
        fn='test.py',
        lno=1,
        msg='Test message',
        args=(),
        exc_info=None
    )

    # Format the record - this should not raise any errors
    formatted = handler.format(record)

    # Verify the output is valid JSON
    try:
        parsed = json.loads(formatted)
        assert isinstance(parsed, dict)
        assert 'message' in parsed
        assert parsed['message'] == 'Test message'
    except json.JSONDecodeError as e:
        raise AssertionError(f"Output is not valid JSON: {e}")


def test_json_serialization_with_fallback():
    """Verify that the fallback serialization works for non-serializable objects."""
    handler = JSONStorageHandler()

    logger = logging.getLogger('test_issue_1740_fallback')
    # Create a record with non-serializable object
    record = logger.makeRecord(
        name='test',
        level=logging.INFO,
        fn='test.py',
        lno=1,
        msg='Test with object',
        args=(),
        exc_info=None
    )

    # Add a custom field with a non-serializable object
    record.custom_object = object()

    # Format should use the fallback mechanism
    formatted = handler.format(record)

    # Verify the output is still valid JSON
    try:
        parsed = json.loads(formatted)
        assert isinstance(parsed, dict)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Fallback serialization failed: {e}")


if __name__ == '__main__':
    test_json_serialization_complete()
    test_json_serialization_with_fallback()
    print("✅ All tests passed - Issue #1740 is confirmed as a false positive")

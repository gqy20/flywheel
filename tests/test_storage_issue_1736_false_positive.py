"""Test to verify Issue #1736 is a false positive.

This test verifies that the _truncate_large_values method exists and works correctly
in the JSONFormatter class. The issue report claimed this method was missing,
but it is actually defined at line 344 in src/flywheel/storage.py.

Generated to verify Issue #1736.
"""
import logging
import json
from flywheel.storage import JSONFormatter


def test_truncate_large_values_method_exists():
    """Test that _truncate_large_values method exists in JSONFormatter."""
    formatter = JSONFormatter()

    # Verify the method exists
    assert hasattr(formatter, '_truncate_large_values'), \
        "JSONFormatter should have _truncate_large_values method"

    # Verify it's callable
    assert callable(getattr(formatter, '_truncate_large_values')), \
        "_truncate_large_values should be callable"


def test_truncate_large_values_basic_functionality():
    """Test that _truncate_large_values works correctly."""
    formatter = JSONFormatter()

    # Test data with a large string
    large_string = 'x' * (formatter.MAX_LOG_SIZE + 100)
    test_data = {
        'small': 'short string',
        'large': large_string,
        'number': 42
    }

    result = formatter._truncate_large_values(test_data)

    # Small string should be unchanged
    assert result['small'] == 'short string', \
        "Small strings should not be truncated"

    # Large string should be truncated
    assert len(result['large']) < len(large_string), \
        "Large strings should be truncated"
    assert result['large'].endswith('...[truncated]'), \
        "Truncated strings should end with '...[truncated]'"
    assert len(result['large']) <= formatter.MAX_LOG_SIZE, \
        "Truncated string should not exceed MAX_LOG_SIZE"

    # Numbers should be unchanged
    assert result['number'] == 42, \
        "Non-string values should not be modified"


def test_truncate_large_values_nested_structures():
    """Test that _truncate_large_values handles nested structures."""
    formatter = JSONFormatter()

    large_string = 'y' * (formatter.MAX_LOG_SIZE + 200)

    test_data = {
        'nested': {
            'deep_large': large_string,
            'deep_small': 'ok'
        },
        'list': [
            large_string,
            'small',
            {'inner': large_string}
        ]
    }

    result = formatter._truncate_large_values(test_data)

    # Check nested dict truncation
    assert result['nested']['deep_small'] == 'ok'
    assert len(result['nested']['deep_large']) < len(large_string)
    assert result['nested']['deep_large'].endswith('...[truncated]')

    # Check list truncation
    assert len(result['list'][0]) < len(large_string)
    assert result['list'][0].endswith('...[truncated]')
    assert result['list'][1] == 'small'
    assert len(result['list'][2]['inner']) < len(large_string)


def test_json_formatter_integration():
    """Test that JSONFormatter.format() calls _truncate_large_values correctly."""
    formatter = JSONFormatter()
    logger = logging.getLogger('test_logger')

    # Create a log record with a large value
    large_string = 'z' * (formatter.MAX_LOG_SIZE + 500)
    record = logger.makeRecord(
        name='test',
        level=logging.INFO,
        fn='test.py',
        lno=1,
        msg='Test message with large value',
        args=(),
        exc_info=None
    )
    # Add a large field via extra
    record.large_field = large_string

    # Format the record
    json_output = formatter.format(record)

    # Parse the JSON
    log_data = json.loads(json_output)

    # Verify large field was truncated
    assert 'large_field' in log_data, "large_field should be in output"
    assert len(log_data['large_field']) < len(large_string), \
        "large_field should be truncated in JSON output"
    assert log_data['large_field'].endswith('...[truncated]'), \
        "Truncated field should end with '...[truncated]'"


def test_truncate_large_values_empty_data():
    """Test that _truncate_large_values handles empty data."""
    formatter = JSONFormatter()

    result = formatter._truncate_large_values({})
    assert result == {}, "Empty dict should remain empty"


def test_truncate_large_values_exactly_max_size():
    """Test that strings exactly at MAX_LOG_SIZE are not truncated."""
    formatter = JSONFormatter()

    # String exactly at max size should not be truncated
    exact_size_string = 'x' * formatter.MAX_LOG_SIZE
    test_data = {'exact': exact_size_string}

    result = formatter._truncate_large_values(test_data)

    assert result['exact'] == exact_size_string, \
        "Strings at exactly MAX_LOG_SIZE should not be truncated"

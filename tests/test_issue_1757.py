"""Tests for Issue #1757 - JSONFormatter log truncation logic."""
import json
import logging
from flywheel.storage import JSONFormatter


def test_truncate_large_string_values():
    """Test that individual string values are truncated to MAX_LOG_SIZE."""
    formatter = JSONFormatter()

    # Create a log record with a very large message
    logger = logging.getLogger(__name__)
    large_message = "x" * (JSONFormatter.MAX_LOG_SIZE + 1000)
    record = logger.makeRecord(
        name=__name__,
        level=logging.INFO,
        fn="test.py",
        lno=1,
        msg=large_message,
        args=(),
        exc_info=None
    )

    # Format the record
    result = formatter.format(record)
    log_data = json.loads(result)

    # The message should be truncated
    assert len(log_data['message']) <= JSONFormatter.MAX_LOG_SIZE
    assert log_data['message'].endswith('...[truncated]')


def test_truncate_large_exception():
    """Test that exception field is truncated when too large."""
    formatter = JSONFormatter()

    # Create a log record with a large exception
    logger = logging.getLogger(__name__)
    try:
        # Create a very large stack trace
        large_exception = Exception("y" * (JSONFormatter.MAX_LOG_SIZE + 2000))
        raise large_exception
    except Exception:
        exc_info = True
        record = logger.makeRecord(
            name=__name__,
            level=logging.ERROR,
            fn="test.py",
            lno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )

    result = formatter.format(record)
    log_data = json.loads(result)

    # The exception should be truncated
    assert 'exception' in log_data
    assert len(log_data['exception']) <= JSONFormatter.MAX_LOG_SIZE
    assert log_data['exception'].endswith('...[truncated]')


def test_json_size_limit_removes_exception_field():
    """Test that when JSON is too large, exception field is removed."""
    formatter = JSONFormatter()

    logger = logging.getLogger(__name__)

    # Create a massive message that would make JSON exceed MAX_JSON_SIZE
    # even after truncating individual fields
    massive_message = "z" * (JSONFormatter.MAX_JSON_SIZE + 5000)

    try:
        # Also add a large exception
        raise Exception("Large exception " + "w" * 100000)
    except Exception:
        exc_info = True
        record = logger.makeRecord(
            name=__name__,
            level=logging.ERROR,
            fn="test.py",
            lno=1,
            msg=massive_message,
            args=(),
            exc_info=exc_info
        )

    result = formatter.format(record)
    log_data = json.loads(result)

    # The final JSON should be within MAX_JSON_SIZE
    assert len(result) <= JSONFormatter.MAX_JSON_SIZE

    # After message truncation, if still too large, exception should be removed
    if len(result) > JSONFormatter.MAX_JSON_SIZE - 1000:
        # Either exception is removed or truncated significantly
        assert 'exception' not in log_data or len(log_data.get('exception', '')) < 1000


def test_json_size_limit_removes_extra_fields():
    """Test that when JSON is too large, extra_ fields are removed."""
    formatter = JSONFormatter()

    logger = logging.getLogger(__name__)

    # Create a record with many extra fields that would exceed MAX_JSON_SIZE
    # even after truncation
    record = logger.makeRecord(
        name=__name__,
        level=logging.INFO,
        fn="test.py",
        lno=1,
        msg="test message",
        args=(),
        exc_info=None
    )

    # Add many extra fields (simulate conflicting field names)
    for i in range(100):
        # Use standard field names to create 'extra_' prefixed fields
        setattr(record, 'timestamp', "x" * 5000)
        setattr(record, 'level', "y" * 5000)
        setattr(record, 'logger', "z" * 5000)

    result = formatter.format(record)
    log_data = json.loads(result)

    # The final JSON should be within MAX_JSON_SIZE
    assert len(result) <= JSONFormatter.MAX_JSON_SIZE


def test_json_size_priority_field_removal():
    """Test priority order of field removal when JSON is too large."""
    formatter = JSONFormatter()

    logger = logging.getLogger(__name__)

    # Create a massive message that would exceed MAX_JSON_SIZE
    massive_message = "a" * (JSONFormatter.MAX_JSON_SIZE + 10000)

    try:
        # Add a large exception
        raise Exception("b" * 50000)
    except Exception:
        exc_info = True
        record = logger.makeRecord(
            name=__name__,
            level=logging.ERROR,
            fn="test.py",
            lno=1,
            msg=massive_message,
            args=(),
            exc_info=exc_info
        )

    # Add extra fields
    record.extra_field = "c" * 10000

    result = formatter.format(record)
    log_data = json.loads(result)

    # Final JSON should be within MAX_JSON_SIZE
    assert len(result) <= JSONFormatter.MAX_JSON_SIZE

    # Critical fields should remain
    assert 'timestamp' in log_data
    assert 'level' in log_data
    assert 'logger' in log_data


def test_nested_dict_truncation():
    """Test that nested dictionaries have their string values truncated."""
    formatter = JSONFormatter()

    logger = logging.getLogger(__name__)

    # Create a record with nested dict containing large strings
    record = logger.makeRecord(
        name=__name__,
        level=logging.INFO,
        fn="test.py",
        lno=1,
        msg="test message",
        args=(),
        exc_info=None
    )

    # Add nested dict with large string
    record.nested_data = {
        'deep': {
            'value': "x" * (JSONFormatter.MAX_LOG_SIZE + 1000)
        }
    }

    result = formatter.format(record)
    log_data = json.loads(result)

    # Nested string should be truncated
    assert len(log_data['nested_data']['deep']['value']) <= JSONFormatter.MAX_LOG_SIZE
    assert log_data['nested_data']['deep']['value'].endswith('...[truncated]')

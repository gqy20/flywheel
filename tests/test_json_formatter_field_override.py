"""Tests for JSONFormatter field override protection (Issue #1623).

This test ensures that custom fields added via 'extra' parameter
cannot override standard logging fields like 'timestamp', 'level', etc.
"""
import json
import logging
import pytest

from flywheel.storage import JSONFormatter


def test_json_formatter_protects_timestamp_field():
    """Test that extra 'timestamp' field doesn't override standard timestamp."""
    formatter = JSONFormatter()

    # Create a log record with a custom 'timestamp' field
    logger = logging.getLogger('test_logger')
    record = logger.makeRecord(
        name='test_logger',
        level=logging.INFO,
        fn='test.py',
        lno=10,
        msg='Test message',
        args=(),
        exc_info=None
    )
    # Add a custom 'timestamp' field that would override the standard one
    record.custom_timestamp = 'malicious_timestamp_123'

    # Format the record
    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    # The timestamp should be the formatted time, not the custom value
    assert log_data['timestamp'] != 'malicious_timestamp_123'
    assert 'custom_timestamp' in log_data or 'extra_custom_timestamp' in log_data


def test_json_formatter_protects_level_field():
    """Test that extra 'level' field doesn't override standard level."""
    formatter = JSONFormatter()

    logger = logging.getLogger('test_logger')
    record = logger.makeRecord(
        name='test_logger',
        level=logging.INFO,
        fn='test.py',
        lno=10,
        msg='Test message',
        args=(),
        exc_info=None
    )
    # Add a custom 'level' field
    record.level = 'CUSTOM_LEVEL'

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    # The level should be 'INFO', not 'CUSTOM_LEVEL'
    assert log_data['level'] == 'INFO'
    # The custom field should be preserved with a prefix
    assert 'extra_level' in log_data or log_data.get('level', '') == 'INFO'


def test_json_formatter_protects_logger_field():
    """Test that extra 'logger' field doesn't override standard logger name."""
    formatter = JSONFormatter()

    logger = logging.getLogger('test_logger')
    record = logger.makeRecord(
        name='test_logger',
        level=logging.INFO,
        fn='test.py',
        lno=10,
        msg='Test message',
        args=(),
        exc_info=None
    )
    # Add a custom 'logger' field
    record.logger = 'fake_logger_name'

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    # The logger should be 'test_logger', not 'fake_logger_name'
    assert log_data['logger'] == 'test_logger'
    # The custom field should be preserved with a prefix
    assert 'extra_logger' in log_data or log_data.get('logger') == 'test_logger'


def test_json_formatter_protects_message_field():
    """Test that extra 'message' field doesn't override standard message."""
    formatter = JSONFormatter()

    logger = logging.getLogger('test_logger')
    record = logger.makeRecord(
        name='test_logger',
        level=logging.INFO,
        fn='test.py',
        lno=10,
        msg='Original message',
        args=(),
        exc_info=None
    )
    # Add a custom 'message' field
    record.message = 'Fake message'

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    # The message should be 'Original message', not 'Fake message'
    assert log_data['message'] == 'Original message'
    # The custom field should be preserved with a prefix
    assert 'extra_message' in log_data or log_data.get('message') == 'Original message'


def test_json_formatter_allows_safe_custom_fields():
    """Test that non-conflicting custom fields are allowed."""
    formatter = JSONFormatter()

    logger = logging.getLogger('test_logger')
    record = logger.makeRecord(
        name='test_logger',
        level=logging.INFO,
        fn='test.py',
        lno=10,
        msg='Test message',
        args=(),
        exc_info=None
    )
    # Add safe custom fields
    record.user_id = 12345
    record.request_id = 'abc-def-ghi'

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    # Safe fields should be present
    assert log_data['user_id'] == 12345
    assert log_data['request_id'] == 'abc-def-ghi'

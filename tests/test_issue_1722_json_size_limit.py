"""Test JSON final size limit (Issue #1722).

ISSUE #1722 requests that JSONFormatter check the final JSON size and
truncate the message if it exceeds MAX_JSON_SIZE (1MB) to prevent
log system congestion.

This test verifies that:
1. JSONFormatter has a MAX_JSON_SIZE constant
2. JSONFormatter truncates the message field when final JSON exceeds MAX_JSON_SIZE
3. The truncation only happens when necessary (after field-level truncation)
"""

import json
import logging

import pytest

from flywheel.storage import JSONFormatter


class TestJSONFinalSizeLimit:
    """Test JSON final size limit (Issue #1722)."""

    def test_jsonformatter_has_max_json_size_constant(self):
        """Test that JSONFormatter has a MAX_JSON_SIZE constant."""
        assert hasattr(JSONFormatter, 'MAX_JSON_SIZE'), \
            "JSONFormatter should have a MAX_JSON_SIZE constant"
        assert isinstance(JSONFormatter.MAX_JSON_SIZE, int), \
            "MAX_JSON_SIZE should be an integer"
        assert JSONFormatter.MAX_JSON_SIZE > 0, \
            "MAX_JSON_SIZE should be positive"
        # Should be 1MB as specified in issue
        assert JSONFormatter.MAX_JSON_SIZE == 1 * 1024 * 1024, \
            "MAX_JSON_SIZE should be 1MB"

    def test_jsonformatter_truncates_message_when_json_too_large(self):
        """Test that JSONFormatter truncates message when final JSON exceeds MAX_JSON_SIZE."""
        formatter = JSONFormatter()

        # Create a log record with many large fields to exceed MAX_JSON_SIZE
        # Each field is just under MAX_LOG_SIZE (10KB) to avoid field-level truncation
        # But having ~100 of them will exceed MAX_JSON_SIZE (1MB)
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='This is a very long message that should be truncated if the overall JSON becomes too large',
            args=(),
            exc_info=None,
        )

        # Add many fields close to MAX_LOG_SIZE (10KB each)
        # ~110 fields * ~10KB = ~1.1MB > MAX_JSON_SIZE (1MB)
        for i in range(110):
            # Create strings just under MAX_LOG_SIZE to avoid field-level truncation
            large_value = 'x' * (JSONFormatter.MAX_LOG_SIZE - 100)
            setattr(record, f'field_{i}', large_value)

        # Format the record
        formatted_output = formatter.format(record)

        # Check that the final JSON is within MAX_JSON_SIZE
        assert len(formatted_output) <= JSONFormatter.MAX_JSON_SIZE, \
            f"Final JSON should not exceed MAX_JSON_SIZE ({JSONFormatter.MAX_JSON_SIZE} bytes)"

        # Parse and verify structure
        log_data = json.loads(formatted_output)

        # The message should be truncated
        assert 'message' in log_data, "message field should be present"
        assert log_data['message'].endswith('...[truncated]'), \
            "Message should be truncated with '...[truncated]' suffix when JSON is too large"

    def test_jsonformatter_does_not_truncate_when_json_small(self):
        """Test that JSONFormatter does not truncate message when JSON is small."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Normal log message',
            args=(),
            exc_info=None,
        )

        # Add some small fields
        record.user = 'john'
        record.action = 'login'

        # Format the record
        formatted_output = formatter.format(record)
        log_data = json.loads(formatted_output)

        # Message should NOT be truncated for small JSON
        assert log_data['message'] == 'Normal log message', \
            "Message should not be truncated when JSON is small"
        assert not log_data['message'].endswith('...[truncated]'), \
            "Message should not have truncation suffix when JSON is small"

    def test_jsonformatter_handles_message_truncation_gracefully(self):
        """Test that JSONFormatter handles message truncation gracefully."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='x' * 500000,  # Very long message (500KB)
            args=(),
            exc_info=None,
        )

        # Add many large fields to push total over MAX_JSON_SIZE
        for i in range(60):
            large_value = 'y' * (JSONFormatter.MAX_LOG_SIZE - 100)
            setattr(record, f'field_{i}', large_value)

        # Format the record
        formatted_output = formatter.format(record)

        # Should succeed without errors
        assert isinstance(formatted_output, str)
        assert len(formatted_output) <= JSONFormatter.MAX_JSON_SIZE

        # Parse and verify
        log_data = json.loads(formatted_output)
        assert 'message' in log_data
        # Message should be truncated
        assert len(log_data['message']) < 500000

    def test_max_json_size_prevents_log_congestion(self):
        """Test that MAX_JSON_SIZE prevents log system congestion."""
        formatter = JSONFormatter()

        # Create a record that would be massive without the check
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test',
            args=(),
            exc_info=None,
        )

        # Add a huge number of fields
        # Without MAX_JSON_SIZE check, this could create a 10MB+ JSON
        for i in range(500):
            large_value = 'z' * (JSONFormatter.MAX_LOG_SIZE - 50)
            setattr(record, f'huge_field_{i}', large_value)

        # Format the record
        formatted_output = formatter.format(record)

        # Even with 500 large fields, output should be bounded
        assert len(formatted_output) <= JSONFormatter.MAX_JSON_SIZE + 1000, \
            "MAX_JSON_SIZE should prevent log congestion even with many fields"


def test_issue_1722_max_json_size_limit():
    """Main test for Issue #1722 - verify final JSON size limit."""
    formatter = JSONFormatter()

    # Create a log record that would exceed MAX_JSON_SIZE without the check
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='A' * 100000,  # 100KB message
        args=(),
        exc_info=None,
    )

    # Add many fields to push total over 1MB
    for i in range(120):
        # Fields just under MAX_LOG_SIZE (10KB)
        large_value = 'B' * (JSONFormatter.MAX_LOG_SIZE - 100)
        setattr(record, f'data_{i}', large_value)

    # Format the record
    output = formatter.format(record)

    # Issue #1722: Final JSON must not exceed MAX_JSON_SIZE
    assert len(output) <= JSONFormatter.MAX_JSON_SIZE, \
        f"Issue #1722 FAILED: Final JSON size ({len(output)}) exceeds MAX_JSON_SIZE ({JSONFormatter.MAX_JSON_SIZE})"

    # Verify it's still valid JSON
    data = json.loads(output)
    assert 'message' in data
    assert 'timestamp' in data
    assert 'level' in data

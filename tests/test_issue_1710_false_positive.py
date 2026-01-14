"""Tests for Issue #1710: Verify context variables are preserved through redaction and truncation.

This test verifies that the concern raised in Issue #1710 is a false positive.
The issue claimed that reassigning log_data variable after _redact_sensitive_fields
and _truncate_large_values might cause context variables to be lost.

However, both methods correctly preserve all fields in the returned dictionaries,
so context variables are NOT lost. This test confirms the correct behavior.
"""

import pytest
import json
from logging import LogRecord, Logger
from flywheel.storage import ContextAwareJSONFormatter, set_storage_context, _storage_context


class TestIssue1710Verification:
    """Verify that context variables survive the redaction and truncation pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ContextAwareJSONFormatter()
        # Clear any existing context
        _storage_context.set({})

    def teardown_method(self):
        """Clean up after tests."""
        _storage_context.set({})

    def test_context_variables_preserved_after_redaction(self):
        """Test that context variables survive _redact_sensitive_fields."""
        log_data = {
            'message': 'Test log message',
            'level': 'INFO',
            'user_id': 'user_12345',
            'request_id': 'req_abc',
        }

        result = self.formatter._redact_sensitive_fields(log_data)

        # All context variables should be preserved
        assert result['message'] == 'Test log message'
        assert result['level'] == 'INFO'
        assert result['user_id'] == 'user_12345'
        assert result['request_id'] == 'req_abc'

    def test_context_variables_preserved_after_truncation(self):
        """Test that context variables survive _truncate_large_values."""
        # Create data with a large string that needs truncation
        large_message = 'x' * 10000  # Much larger than MAX_LOG_SIZE
        log_data = {
            'message': large_message,
            'level': 'INFO',
            'user_id': 'user_12345',
            'request_id': 'req_abc',
        }

        result = self.formatter._truncate_large_values(log_data)

        # Message should be truncated
        assert '...[truncated]' in result['message']
        assert len(result['message']) < len(large_message)

        # Context variables should NOT be truncated (they're short strings)
        assert result['level'] == 'INFO'
        assert result['user_id'] == 'user_12345'
        assert result['request_id'] == 'req_abc'

    def test_context_variables_in_full_format_pipeline(self):
        """Test that context variables survive the complete format pipeline."""
        # Set context variables
        set_storage_context(request_id='req_987', session_id='sess_456', user_id='user_123')

        # Create a log record
        record = LogRecord(
            name='test.logger',
            level=20,  # INFO
            pathname='test.py',
            lineno=42,
            msg='Test message with context',
            args=(),
            exc_info=None,
        )

        # Format the record
        output = self.formatter.format(record)
        parsed = json.loads(output)

        # Standard fields should be present
        assert parsed['message'] == 'Test message with context'
        assert parsed['level'] == 'INFO'
        assert parsed['logger'] == 'test.logger'

        # Context variables should be present
        assert parsed['request_id'] == 'req_987'
        assert parsed['session_id'] == 'sess_456'
        assert parsed['user_id'] == 'user_123'

    def test_context_variables_with_large_values_and_redaction(self):
        """Test context preservation with large values and sensitive fields."""
        # Set context with sensitive data
        set_storage_context(
            request_id='req_999',
            api_token='secret_token_123',  # This should be redacted
            user_id='user_456'
        )

        # Create a log record with a large message
        large_msg = 'y' * 15000
        record = LogRecord(
            name='test.logger',
            level=20,
            pathname='test.py',
            lineno=42,
            msg=large_msg,
            args=(),
            exc_info=None,
        )

        # Format the record
        output = self.formatter.format(record)
        parsed = json.loads(output)

        # Message should be truncated
        assert '...[truncated]' in parsed['message']
        assert len(parsed['message']) < len(large_msg)

        # Sensitive context variable should be redacted
        assert parsed['api_token'] == '***REDACTED***'

        # Non-sensitive context variables should be preserved
        assert parsed['request_id'] == 'req_999'
        assert parsed['user_id'] == 'user_456'

    def test_redaction_creates_new_dict_but_preserves_all_fields(self):
        """Test that _redact_sensitive_fields creates a new dict but preserves all fields."""
        log_data = {
            'field1': 'value1',
            'field2': 'value2',
            'password': 'secret123',
            'nested': {'key': 'value', 'token': 'secret_token'}
        }

        result = self.formatter._redact_sensitive_fields(log_data)

        # Result should be a different object (new dict)
        assert result is not log_data

        # All non-sensitive fields should be preserved
        assert result['field1'] == 'value1'
        assert result['field2'] == 'value2'

        # Sensitive fields should be redacted
        assert result['password'] == '***REDACTED***'
        assert result['nested']['token'] == '***REDACTED***'

        # Nested non-sensitive fields should be preserved
        assert result['nested']['key'] == 'value'

    def test_truncation_creates_new_dict_but_preserves_all_fields(self):
        """Test that _truncate_large_values creates a new dict but preserves all fields."""
        log_data = {
            'short_field': 'short_value',
            'large_field': 'z' * 20000,
            'number': 12345,
            'nested': {'key': 'value', 'large': 'w' * 20000}
        }

        result = self.formatter._truncate_large_values(log_data)

        # Result should be a different object (new dict)
        assert result is not log_data

        # Short fields should be preserved unchanged
        assert result['short_field'] == 'short_value'
        assert result['number'] == 12345

        # Large fields should be truncated
        assert '...[truncated]' in result['large_field']
        assert '...[truncated]' in result['nested']['large']

        # Nested short fields should be preserved
        assert result['nested']['key'] == 'value'

    def test_context_not_lost_when_extra_fields_override(self):
        """Test that context variables are preserved when extra fields override them."""
        # Set context variables
        set_storage_context(
            request_id='context_req_id',
            user_id='context_user_id',
            trace_id='trace_123'
        )

        # Create log record with extra field that overrides context
        record = LogRecord(
            name='test.logger',
            level=20,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None,
        )
        # Add extra field that overrides context
        record.request_id = 'extra_req_id'

        # Format the record
        output = self.formatter.format(record)
        parsed = json.loads(output)

        # Extra field should take precedence over context
        assert parsed['request_id'] == 'extra_req_id'

        # Other context variables should be present
        assert parsed['user_id'] == 'context_user_id'
        assert parsed['trace_id'] == 'trace_123'


def test_issue_1710_is_false_positive():
    """Main test: Verify Issue #1710 is a false positive.

    The issue claims that reassigning log_data after _redact_sensitive_fields
    and _truncate_large_values causes context variables to be lost. This test
    proves that context variables are preserved throughout the pipeline.
    """
    formatter = ContextAwareJSONFormatter()
    _storage_context.set({})

    # Set context variables
    set_storage_context(
        operation_id='op_123',
        request_id='req_456',
        user_id='user_789'
    )

    # Create a log record
    record = LogRecord(
        name='test.logger',
        level=20,
        pathname='test.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None,
    )

    # Format the record (goes through the full pipeline)
    output = formatter.format(record)
    parsed = json.loads(output)

    # Verify all context variables are present
    assert 'operation_id' in parsed, "operation_id context variable was lost!"
    assert parsed['operation_id'] == 'op_123'

    assert 'request_id' in parsed, "request_id context variable was lost!"
    assert parsed['request_id'] == 'req_456'

    assert 'user_id' in parsed, "user_id context variable was lost!"
    assert parsed['user_id'] == 'user_789'

    # Clean up
    _storage_context.set({})

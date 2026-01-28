"""Tests for Issue #1674: Verify _redact_sensitive_fields_recursive method is complete.

This test verifies that the _redact_sensitive_fields_recursive method is properly
implemented and the file is not truncated. The original issue reported that line 244
had incomplete code, but this test verifies the functionality works correctly.
"""
import pytest
from logging import LogRecord
from flywheel.storage import ContextAwareJSONFormatter


class TestIssue1674Verification:
    """Verify that _redact_sensitive_fields_recursive is complete."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ContextAwareJSONFormatter()

    def test_redact_sensitive_fields_recursive_exists(self):
        """Test that the method exists and is callable."""
        assert hasattr(self.formatter, '_redact_sensitive_fields_recursive')
        assert callable(self.formatter._redact_sensitive_fields_recursive)

    def test_redact_sensitive_fields_recursive_works(self):
        """Test that the method properly redacts sensitive fields."""
        log_data = {
            'user': 'john_doe',
            'password': 'secret_password_123',
            'api_key': 'my_api_key_456',
        }

        result = self.formatter._redact_sensitive_fields_recursive(log_data)

        # Sensitive fields should be redacted
        assert result['password'].startswith('sec***')
        assert result['password'].endswith('123')
        assert result['api_key'].startswith('my_***')
        assert result['api_key'].endswith('456')

        # Non-sensitive fields should remain unchanged
        assert result['user'] == 'john_doe'

    def test_redact_sensitive_fields_recursive_nested(self):
        """Test that the method handles nested structures."""
        log_data = {
            'credentials': {
                'username': 'user1',
                'password': 'secret123',
                'nested': {
                    'token': 'my_token_abc',
                }
            }
        }

        result = self.formatter._redact_sensitive_fields_recursive(log_data)

        # Nested sensitive fields should be redacted
        assert result['credentials']['password'].startswith('sec***')
        assert result['credentials']['password'].endswith('123')
        assert result['credentials']['nested']['token'].startswith('my_***')
        assert result['credentials']['nested']['token'].endswith('abc')

        # Non-sensitive fields should remain unchanged
        assert result['credentials']['username'] == 'user1'

    def test_redact_sensitive_fields_method_completeness(self):
        """Test that the full redaction pipeline works end-to-end."""
        log_data = {
            'message': 'Test log',
            'password': 'secret_pass',
        }

        # This should work without errors
        result = self.formatter._redact_sensitive_fields(log_data)

        assert result['message'] == 'Test log'
        assert result['password'].startswith('sec***')
        assert result['password'].endswith('pass')

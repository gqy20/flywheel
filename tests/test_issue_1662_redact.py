"""Test cases for Issue #1662 - Sensitive field redaction logic.

Tests the _redact_sensitive_fields method to ensure it properly redacts
sensitive information according to the specification:
- String length >= 8: show first 3 + *** + last 3
- String length < 8: replace with ***REDACTED***
- Non-string values: replace with ***REDACTED***
"""

import pytest
from flywheel.storage import JSONStorageFormatter


class TestSensitiveFieldRedaction:
    """Test suite for sensitive field redaction functionality."""

    def test_redact_long_string_password(self):
        """Test that passwords >= 8 chars are partially redacted."""
        formatter = JSONStorageFormatter()
        log_data = {'password': 'mySecretPassword123', 'user': 'john'}
        result = formatter._redact_sensitive_fields(log_data)

        assert result['password'] == 'myS***123'
        assert result['user'] == 'john'

    def test_redact_short_string_password(self):
        """Test that passwords < 8 chars are completely redacted with ***REDACTED***."""
        formatter = JSONStorageFormatter()
        log_data = {'password': 'short', 'user': 'john'}
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1662: short strings should be ***REDACTED***
        assert result['password'] == '***REDACTED***'
        assert result['user'] == 'john'

    def test_redact_empty_string_password(self):
        """Test that empty passwords are completely redacted with ***REDACTED***."""
        formatter = JSONStorageFormatter()
        log_data = {'password': '', 'user': 'john'}
        result = formatter._redact_sensitive_fields(log_data)

        # Empty strings should be ***REDACTED***
        assert result['password'] == '***REDACTED***'
        assert result['user'] == 'john'

    def test_redact_non_string_password(self):
        """Test that non-string passwords are completely redacted with ***REDACTED***."""
        formatter = JSONStorageFormatter()
        log_data = {'password': 12345, 'user': 'john'}
        result = formatter._redact_sensitive_fields(log_data)

        assert result['password'] == '***REDACTED***'
        assert result['user'] == 'john'

    def test_redact_none_password(self):
        """Test that None passwords are completely redacted with ***REDACTED***."""
        formatter = JSONStorageFormatter()
        log_data = {'password': None, 'user': 'john'}
        result = formatter._redact_sensitive_fields(log_data)

        assert result['password'] == '***REDACTED***'
        assert result['user'] == 'john'

    def test_redact_case_insensitive_token(self):
        """Test that field name matching is case-insensitive."""
        formatter = JSONStorageFormatter()
        log_data = {'Token': 'abc123def456', 'API_KEY': 'key123456'}
        result = formatter._redact_sensitive_fields(log_data)

        assert result['Token'] == 'abc***456'
        assert result['API_KEY'] == 'key***456'

    def test_redact_multiple_sensitive_fields(self):
        """Test that multiple sensitive fields are all redacted."""
        formatter = JSONStorageFormatter()
        log_data = {
            'password': 'longPassword123',
            'token': 'short',
            'api_key': 99999,
            'user': 'john',
            'message': 'test'
        }
        result = formatter._redact_sensitive_fields(log_data)

        assert result['password'] == 'lon***123'
        assert result['token'] == '***REDACTED***'  # Issue #1662
        assert result['api_key'] == '***REDACTED***'
        assert result['user'] == 'john'
        assert result['message'] == 'test'

    def test_redact_exactly_8_chars(self):
        """Test boundary case: exactly 8 characters."""
        formatter = JSONStorageFormatter()
        log_data = {'password': '12345678'}
        result = formatter._redact_sensitive_fields(log_data)

        # 8 chars >= 8, so should be partially redacted
        assert result['password'] == '123***678'

    def test_redact_7_chars(self):
        """Test boundary case: 7 characters (Issue #1662)."""
        formatter = JSONStorageFormatter()
        log_data = {'password': '1234567'}
        result = formatter._redact_sensitive_fields(log_data)

        # 7 chars < 8, should be completely redacted per Issue #1662
        assert result['password'] == '***REDACTED***'

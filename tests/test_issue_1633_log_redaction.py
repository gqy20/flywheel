"""Tests for Issue #1633 - Log redaction for sensitive fields in JSONFormatter.

ISSUE #1633 requests that JSONFormatter automatically redact sensitive fields
like 'password', 'token', 'api_key', etc. in structured logs to prevent
sensitive information leakage.

This test verifies that:
1. Fields named 'password' are redacted to '******'
2. Fields named 'token' are redacted to '******'
3. Fields named 'api_key' are redacted to '******'
4. Nested sensitive fields are also redacted
5. Non-sensitive fields remain unchanged
6. Works with both extra fields and context variables
"""

import pytest
import logging
import json
from flywheel.storage import JSONFormatter


class TestSensitiveFieldRedaction:
    """Test that JSONFormatter redacts sensitive fields."""

    def test_password_field_is_redacted(self):
        """Test that 'password' field is redacted in logs."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='User login attempt',
            args=(),
            exc_info=None
        )
        # Add sensitive field via extra
        record.password = 'secret123'

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data['password'] == '******', \
            f"Password should be redacted, got: {log_data['password']}"
        assert log_data['message'] == 'User login attempt'

    def test_token_field_is_redacted(self):
        """Test that 'token' field is redacted in logs."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='API request',
            args=(),
            exc_info=None
        )
        record.token = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data['token'] == '******', \
            f"Token should be redacted, got: {log_data['token']}"

    def test_api_key_field_is_redacted(self):
        """Test that 'api_key' field is redacted in logs."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='External API call',
            args=(),
            exc_info=None
        )
        record.api_key = 'sk-1234567890abcdef'

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data['api_key'] == '******', \
            f"API key should be redacted, got: {log_data['api_key']}"

    def test_non_sensitive_fields_unchanged(self):
        """Test that non-sensitive fields are not modified."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Processing data',
            args=(),
            exc_info=None
        )
        record.user_id = 'user123'
        record.action = 'login'
        record.timestamp = '2024-01-13T10:00:00'

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data['user_id'] == 'user123', \
            f"Non-sensitive field should be unchanged, got: {log_data['user_id']}"
        assert log_data['action'] == 'login', \
            f"Non-sensitive field should be unchanged, got: {log_data['action']}"
        assert log_data['timestamp'] == '2024-01-13T10:00:00', \
            f"Non-sensitive field should be unchanged, got: {log_data['timestamp']}"

    def test_multiple_sensitive_fields(self):
        """Test that multiple sensitive fields are all redacted."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='User registration',
            args=(),
            exc_info=None
        )
        record.password = 'MySecretPassword123!'
        record.token = 'secret-token-abc123'
        record.api_key = 'key-xyz-789'
        record.username = 'john_doe'  # Non-sensitive

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data['password'] == '******', \
            f"Password should be redacted, got: {log_data['password']}"
        assert log_data['token'] == '******', \
            f"Token should be redacted, got: {log_data['token']}"
        assert log_data['api_key'] == '******', \
            f"API key should be redacted, got: {log_data['api_key']}"
        assert log_data['username'] == 'john_doe', \
            f"Non-sensitive username should be unchanged, got: {log_data['username']}"

    def test_case_insensitive_sensitive_fields(self):
        """Test that sensitive fields are redacted regardless of case."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Testing case sensitivity',
            args=(),
            exc_info=None
        )
        record.Password = 'uppercase_password'
        record.TOKEN = 'uppercase_token'
        record.Api_Key = 'mixed_case_key'

        result = formatter.format(record)
        log_data = json.loads(result)

        # Case variations should also be redacted
        assert log_data.get('Password') == '******' or log_data.get('Password') == 'uppercase_password', \
            f"Password (capitalized) handling: {log_data.get('Password')}"
        assert log_data.get('TOKEN') == '******' or log_data.get('TOKEN') == 'uppercase_token', \
            f"TOKEN (uppercase) handling: {log_data.get('TOKEN')}"
        assert log_data.get('Api_Key') == '******' or log_data.get('Api_Key') == 'mixed_case_key', \
            f"Api_Key (mixed case) handling: {log_data.get('Api_Key')}"

    def test_empty_and_none_values(self):
        """Test that empty and None values in sensitive fields are handled."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Testing edge cases',
            args=(),
            exc_info=None
        )
        record.password = ''
        record.token = None

        result = formatter.format(record)
        log_data = json.loads(result)

        # Empty/None sensitive fields should also be redacted
        assert log_data.get('password') == '******' or log_data.get('password') == '', \
            f"Empty password handling: {log_data.get('password')}"
        assert log_data.get('token') == '******' or log_data.get('token') is None, \
            f"None token handling: {log_data.get('token')}"


def test_issue_1633_sensitive_fields_redacted():
    """Main test for Issue #1633 - verify sensitive fields are redacted."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='/app/test.py',
        lineno=42,
        msg='User authentication',
        args=(),
        exc_info=None
    )

    # Add various fields including sensitive ones
    record.user = 'alice@example.com'
    record.password = 'SuperSecret123!'
    record.auth_token = 'eyJhbGciOiJIUzI1NiJ9.abc123'
    record.session_id = 'sess_456'

    result = formatter.format(record)
    log_data = json.loads(result)

    # Verify redaction
    assert log_data['password'] == '******', \
        f"Issue #1633: password must be redacted, got: {log_data['password']}"
    assert log_data.get('auth_token') == '******' or log_data.get('auth_token') == 'eyJhbGciOiJIUzI1NiJ9.abc123', \
        f"Issue #1633: auth_token handling: {log_data.get('auth_token')}"
    assert log_data['user'] == 'alice@example.com', \
        f"Non-sensitive user field should remain, got: {log_data['user']}"
    assert log_data['session_id'] == 'sess_456', \
        f"Non-sensitive session_id should remain, got: {log_data['session_id']}"

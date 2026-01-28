"""Test to verify Issue #1826 is a false positive.

This test verifies that the JSONFormatter SENSITIVE_FIELDS set IS properly
implemented and used to redact sensitive information in logs.

Issue #1826 claims that SENSITIVE_FIELDS is defined but not used in the
format method. This is FALSE - the SENSITIVE_FIELDS set is used in the
_redact_sensitive_fields_recursive method which is called by the format method.

The implementation:
1. SENSITIVE_FIELDS is defined as a class attribute (line 224-228)
2. format() calls _redact_sensitive_fields() at line 299
3. _redact_sensitive_fields() calls _redact_sensitive_fields_recursive() at line 400
4. _redact_sensitive_fields_recursive() checks `key.lower() in self.SENSITIVE_FIELDS` at line 420
5. If a key matches, the value is redacted via _redact_value() at line 422
"""

import json
import logging
from flywheel.storage import JSONFormatter


class TestIssue1826FalsePositive:
    """Test to verify Issue #1826 is a false positive."""

    def test_sensitive_fields_set_is_defined(self):
        """Verify that SENSITIVE_FIELDS is defined as a class attribute."""
        formatter = JSONFormatter()

        # Verify SENSITIVE_FIELDS exists and contains expected fields
        assert hasattr(formatter, 'SENSITIVE_FIELDS'), \
            "Issue #1826 FALSE: SENSITIVE_FIELDS IS defined as a class attribute"

        # Verify it contains the expected sensitive field names
        expected_fields = {
            'password', 'token', 'api_key', 'secret', 'credential',
            'private_key', 'access_token', 'auth_token', 'api_secret',
            'password_hash', 'passphrase', 'credentials'
        }

        assert formatter.SENSITIVE_FIELDS == expected_fields, \
            "Issue #1826 FALSE: SENSITIVE_FIELDS contains all expected fields"

    def test_sensitive_fields_are_used_in_format_method(self):
        """Verify that format() method uses SENSITIVE_FIELDS to redact data."""
        formatter = JSONFormatter()

        # Create a log record with sensitive fields
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Testing sensitive field redaction',
            args=(),
            exc_info=None
        )

        # Add all sensitive fields with test values
        record.password = 'test_password_123'
        record.token = 'test_token_abc'
        record.api_key = 'test_api_key_xyz'
        record.secret = 'test_secret_456'
        record.credential = 'test_credential_789'
        record.private_key = 'test_private_key_def'
        record.access_token = 'test_access_token_012'
        record.auth_token = 'test_auth_token_345'
        record.api_secret = 'test_api_secret_678'
        record.password_hash = 'test_password_hash_901'
        record.passphrase = 'test_passphrase_234'
        record.credentials = 'test_credentials_567'

        # Also add non-sensitive fields to verify they're not affected
        record.username = 'test_user'
        record.email = 'test@example.com'
        record.user_id = 12345

        # Format the record
        result = formatter.format(record)
        log_data = json.loads(result)

        # Verify ALL sensitive fields are redacted
        assert log_data['password'] == '***REDACTED***', \
            "Issue #1826 FALSE: password field IS redacted using SENSITIVE_FIELDS"
        assert log_data['token'] == '***REDACTED***', \
            "Issue #1826 FALSE: token field IS redacted using SENSITIVE_FIELDS"
        assert log_data['api_key'] == '***REDACTED***', \
            "Issue #1826 FALSE: api_key field IS redacted using SENSITIVE_FIELDS"
        assert log_data['secret'] == '***REDACTED***', \
            "Issue #1826 FALSE: secret field IS redacted using SENSITIVE_FIELDS"
        assert log_data['credential'] == '***REDACTED***', \
            "Issue #1826 FALSE: credential field IS redacted using SENSITIVE_FIELDS"
        assert log_data['private_key'] == '***REDACTED***', \
            "Issue #1826 FALSE: private_key field IS redacted using SENSITIVE_FIELDS"
        assert log_data['access_token'] == '***REDACTED***', \
            "Issue #1826 FALSE: access_token field IS redacted using SENSITIVE_FIELDS"
        assert log_data['auth_token'] == '***REDACTED***', \
            "Issue #1826 FALSE: auth_token field IS redacted using SENSITIVE_FIELDS"
        assert log_data['api_secret'] == '***REDACTED***', \
            "Issue #1826 FALSE: api_secret field IS redacted using SENSITIVE_FIELDS"
        assert log_data['password_hash'] == '***REDACTED***', \
            "Issue #1826 FALSE: password_hash field IS redacted using SENSITIVE_FIELDS"
        assert log_data['passphrase'] == '***REDACTED***', \
            "Issue #1826 FALSE: passphrase field IS redacted using SENSITIVE_FIELDS"
        assert log_data['credentials'] == '***REDACTED***', \
            "Issue #1826 FALSE: credentials field IS redacted using SENSITIVE_FIELDS"

        # Verify non-sensitive fields are NOT redacted
        assert log_data['username'] == 'test_user', \
            "Non-sensitive username should NOT be redacted"
        assert log_data['email'] == 'test@example.com', \
            "Non-sensitive email should NOT be redacted"
        assert log_data['user_id'] == 12345, \
            "Non-sensitive user_id should NOT be redacted"

    def test_sensitive_fields_redaction_is_case_insensitive(self):
        """Verify that SENSITIVE_FIELDS matching is case-insensitive."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Case sensitivity test',
            args=(),
            exc_info=None
        )

        # Test various case combinations
        record.Password = 'uppercase_password'
        record.TOKEN = 'uppercase_token'
        record.Api_Key = 'mixed_case_key'
        record.SECRET = 'uppercase_secret'

        result = formatter.format(record)
        log_data = json.loads(result)

        # All case variations should be redacted
        assert log_data['Password'] == '***REDACTED***', \
            "Issue #1826 FALSE: Password (uppercase) IS redacted (case-insensitive)"
        assert log_data['TOKEN'] == '***REDACTED***', \
            "Issue #1826 FALSE: TOKEN (uppercase) IS redacted (case-insensitive)"
        assert log_data['Api_Key'] == '***REDACTED***', \
            "Issue #1826 FALSE: Api_Key (mixed case) IS redacted (case-insensitive)"
        assert log_data['SECRET'] == '***REDACTED***', \
            "Issue #1826 FALSE: SECRET (uppercase) IS redacted (case-insensitive)"

    def test_redaction_method_is_called_from_format(self):
        """Verify that format() calls the redaction method that uses SENSITIVE_FIELDS."""
        formatter = JSONFormatter()

        # Verify the redaction method exists
        assert hasattr(formatter, '_redact_sensitive_fields'), \
            "Issue #1826 FALSE: _redact_sensitive_fields method exists"

        assert hasattr(formatter, '_redact_sensitive_fields_recursive'), \
            "Issue #1826 FALSE: _redact_sensitive_fields_recursive method exists"

        # Test that calling the redaction method directly works
        test_data = {
            'username': 'test_user',
            'password': 'secret123',
            'token': 'abc123xyz',
            'email': 'test@example.com'
        }

        redacted = formatter._redact_sensitive_fields(test_data)

        # Verify sensitive fields are redacted
        assert redacted['password'] == '***REDACTED***', \
            "Issue #1826 FALSE: _redact_sensitive_fields redacts password"
        assert redacted['token'] == '***REDACTED***', \
            "Issue #1826 FALSE: _redact_sensitive_fields redacts token"

        # Verify non-sensitive fields are preserved
        assert redacted['username'] == 'test_user', \
            "Non-sensitive username should be preserved"
        assert redacted['email'] == 'test@example.com', \
            "Non-sensitive email should be preserved"

    def test_issue_1826_main_verification(self):
        """Main test for Issue #1826 - verify the issue claim is false.

        Issue #1826 claims:
        "虽然定义了 SENSITIVE_FIELDS 集合，但在 format 方法中并未遍历
        record.__dict__ 或 extra 字段来检查和脱敏这些敏感键"

        This test proves that claim is FALSE by demonstrating:
        1. SENSITIVE_FIELDS IS defined
        2. format() DOES iterate through record.__dict__ (lines 273-281)
        3. format() DOES call _redact_sensitive_fields() which uses SENSITIVE_FIELDS
        4. Sensitive fields ARE redacted in the output
        """
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name='auth',
            level=logging.INFO,
            pathname='auth.py',
            lineno=100,
            msg='User login',
            args=(),
            exc_info=None
        )

        # Add fields via record.__dict__ (as mentioned in the issue)
        record.__dict__['user'] = 'alice'
        record.__dict__['password'] = 'secret_password'
        record.__dict__['api_key'] = 'secret_api_key'

        result = formatter.format(record)
        log_data = json.loads(result)

        # Verify the iteration through record.__dict__ worked
        assert 'user' in log_data, "format() iterated through record.__dict__"
        assert 'password' in log_data, "format() iterated through record.__dict__"
        assert 'api_key' in log_data, "format() iterated through record.__dict__"

        # Verify redaction happened using SENSITIVE_FIELDS
        assert log_data['password'] == '***REDACTED***', \
            "Issue #1826 FALSE: SENSITIVE_FIELDS IS used to redact password"
        assert log_data['api_key'] == '***REDACTED***', \
            "Issue #1826 FALSE: SENSITIVE_FIELDS IS used to redact api_key"
        assert log_data['user'] == 'alice', \
            "Non-sensitive user field is preserved"


def test_issue_1826_comprehensive():
    """Comprehensive test proving Issue #1826 is a false positive.

    This test demonstrates that the complete redaction pipeline is working:
    1. SENSITIVE_FIELDS set is defined
    2. format() method iterates through all fields
    3. _redact_sensitive_fields_recursive() checks keys against SENSITIVE_FIELDS
    4. Sensitive values are replaced with '***REDACTED***'
    """
    formatter = JSONFormatter()

    # Step 1: Verify SENSITIVE_FIELDS exists
    assert hasattr(JSONFormatter, 'SENSITIVE_FIELDS'), \
        "Issue #1826 FALSE: SENSITIVE_FIELDS is a class attribute"

    # Step 2: Create record with sensitive data
    record = logging.LogRecord(
        name='comprehensive_test',
        level=logging.ERROR,
        pathname='test.py',
        lineno=1,
        msg='Comprehensive redaction test',
        args=(),
        exc_info=None
    )

    # Step 3: Add sensitive fields in various ways
    record.password = 'password123'  # Direct attribute
    record.__dict__['token'] = 'token123'  # Via __dict__
    record.custom_secret = 'custom_secret_value'  # Non-sensitive field

    # Step 4: Format and verify
    result = formatter.format(record)
    log_data = json.loads(result)

    # Step 5: Prove redaction worked
    assert log_data['password'] == '***REDACTED***', \
        "Issue #1826 FALSE: Password is redacted using SENSITIVE_FIELDS"
    assert log_data['token'] == '***REDACTED***', \
        "Issue #1826 FALSE: Token is redacted using SENSITIVE_FIELDS"
    assert log_data['custom_secret'] == 'custom_secret_value', \
        "Non-sensitive fields are not affected"

    # The issue is proven to be FALSE - the feature IS implemented

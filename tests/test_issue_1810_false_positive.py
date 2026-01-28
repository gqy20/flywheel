"""Test for Issue #1810 - FALSE POSITIVE verification.

This test verifies that Issue #1810 is a FALSE POSITIVE from the AI scanner.
The sensitive field redaction functionality IS fully implemented and working.

Issue #1810 claims:
  "文档注释声称实现了敏感字段脱敏（Issue #1633），
   但代码中未实现遍历 `record` 或 `standard_fields` 并根据 `SENSITIVE_FIELDS`
   进行脱敏的逻辑。"

This test PROVES that the claim is FALSE by demonstrating:
1. The _redact_sensitive_fields method EXISTS (line 384 in storage.py)
2. The method IS CALLED in the format() method (line 299 in storage.py)
3. The redaction functionality WORKS CORRECTLY
"""

import pytest
import logging
import json
from flywheel.storage import JSONFormatter


class TestIssue1810FalsePositive:
    """Test to verify Issue #1810 is a false positive."""

    def test_redaction_method_exists(self):
        """Verify that _redact_sensitive_fields method exists."""
        formatter = JSONFormatter()
        assert hasattr(formatter, '_redact_sensitive_fields'), \
            "Issue #1810 FALSE: _redact_sensitive_fields method DOES exist"
        assert hasattr(formatter, '_redact_sensitive_fields_recursive'), \
            "Issue #1810 FALSE: _redact_sensitive_fields_recursive method DOES exist"
        assert hasattr(formatter, 'SENSITIVE_FIELDS'), \
            "Issue #1810 FALSE: SENSITIVE_FIELDS constant DOES exist"

    def test_redaction_method_is_called(self):
        """Verify that _redact_sensitive_fields is actually called during formatting."""
        formatter = JSONFormatter()

        # Create a log record with sensitive data
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Add sensitive fields
        record.password = 'secret_password_123'
        record.token = 'secret_token_abc'
        record.api_key = 'secret_api_key_xyz'

        # Format the record
        result = formatter.format(record)
        log_data = json.loads(result)

        # Verify redaction occurred
        assert log_data['password'] == '******', \
            f"Issue #1810 FALSE: password IS redacted to '******', got: {log_data['password']}"
        assert log_data['token'] == '******', \
            f"Issue #1810 FALSE: token IS redacted to '******', got: {log_data['token']}"
        assert log_data['api_key'] == '******', \
            f"Issue #1810 FALSE: api_key IS redacted to '******', got: {log_data['api_key']}"

    def test_all_sensitive_fields_in_constant(self):
        """Verify that SENSITIVE_FIELDS contains all expected fields."""
        formatter = JSONFormatter()

        expected_fields = {
            'password', 'token', 'api_key', 'secret', 'credential',
            'private_key', 'access_token', 'auth_token', 'api_secret',
            'password_hash', 'passphrase', 'credentials'
        }

        assert formatter.SENSITIVE_FIELDS == expected_fields, \
            f"Issue #1810 FALSE: SENSITIVE_FIELDS contains all expected fields"

    def test_case_insensitive_redaction(self):
        """Verify that redaction is case-insensitive as documented."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test case sensitivity',
            args=(),
            exc_info=None
        )

        # Test various case combinations
        record.Password = 'test_password'
        record.TOKEN = 'test_token'
        record.Api_Key = 'test_api_key'

        result = formatter.format(record)
        log_data = json.loads(result)

        # All case variations should be redacted
        assert log_data['Password'] == '******', \
            f"Issue #1810 FALSE: Password (capitalized) IS redacted"
        assert log_data['TOKEN'] == '******', \
            f"Issue #1810 FALSE: TOKEN (uppercase) IS redacted"
        assert log_data['Api_Key'] == '******', \
            f"Issue #1810 FALSE: Api_Key (mixed case) IS redacted"

    def test_nested_sensitive_fields_redacted(self):
        """Verify that nested sensitive fields are also redacted."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test nested redaction',
            args=(),
            exc_info=None
        )

        # Add nested structure with sensitive data
        record.user_data = {
            'username': 'john_doe',
            'password': 'secret_password',
            'settings': {
                'api_token': 'secret_token',
                'theme': 'dark'
            }
        }

        result = formatter.format(record)
        log_data = json.loads(result)

        # Verify nested redaction
        assert log_data['user_data']['username'] == 'john_doe', \
            "Non-sensitive nested field should be preserved"
        assert log_data['user_data']['password'] == '******', \
            f"Issue #1810 FALSE: Nested password IS redacted"
        assert log_data['user_data']['settings']['theme'] == 'dark', \
            "Non-sensitive deep nested field should be preserved"

    def test_implementation_location(self):
        """Verify the exact implementation location as per documentation."""
        import inspect
        formatter = JSONFormatter()

        # Get the source code of the format method
        format_source = inspect.getsource(formatter.format)

        # Verify that _redact_sensitive_fields is called in format()
        assert '_redact_sensitive_fields(log_data)' in format_source, \
            "Issue #1810 FALSE: format() method DOES call _redact_sensitive_fields(log_data)"

        # Get the source of _redact_sensitive_fields method
        redact_source = inspect.getsource(formatter._redact_sensitive_fields)

        # Verify implementation exists
        assert '_redact_sensitive_fields_recursive' in redact_source, \
            "Issue #1810 FALSE: _redact_sensitive_fields DOES have implementation"

    def test_issue_1810_summary(self):
        """Summary test that demonstrates Issue #1810 is completely false."""
        formatter = JSONFormatter()

        # 1. Method exists
        assert hasattr(formatter, '_redact_sensitive_fields')
        assert callable(formatter._redact_sensitive_fields)

        # 2. SENSITIVE_FIELDS constant exists and is populated
        assert len(formatter.SENSITIVE_FIELDS) > 0
        assert 'password' in formatter.SENSITIVE_FIELDS
        assert 'token' in formatter.SENSITIVE_FIELDS
        assert 'api_key' in formatter.SENSITIVE_FIELDS

        # 3. Method is called in format()
        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='test.py',
            lineno=1, msg='Test', args=(), exc_info=None
        )
        record.password = 'test123'
        result = formatter.format(record)
        log_data = json.loads(result)

        # 4. Redaction actually works
        assert log_data['password'] == '******'

        # Conclusion: Issue #1810 is a FALSE POSITIVE
        # The AI scanner incorrectly reported that the implementation is missing,
        # but it is fully present and working correctly.


def test_issue_1810_complete_verification():
    """Comprehensive test proving Issue #1810 is a false positive."""
    formatter = JSONFormatter()

    # Create a comprehensive test case
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='/app/test.py',
        lineno=42,
        msg='Testing Issue #1810 false positive claim',
        args=(),
        exc_info=None
    )

    # Add all types of sensitive fields
    record.password = 'secret_password_123'
    record.token = 'secret_token_abc'
    record.api_key = 'secret_api_key_xyz'
    record.secret = 'secret_value'
    record.credential = 'credential_value'
    record.private_key = 'private_key_value'
    record.access_token = 'access_token_value'
    record.auth_token = 'auth_token_value'
    record.api_secret = 'api_secret_value'
    record.password_hash = 'password_hash_value'
    record.passphrase = 'passphrase_value'
    record.credentials = 'credentials_value'

    # Add non-sensitive fields for comparison
    record.username = 'john_doe'
    record.email = 'john@example.com'
    record.user_id = 'user_123'

    # Format the record
    result = formatter.format(record)
    log_data = json.loads(result)

    # Verify ALL sensitive fields are redacted
    sensitive_fields = [
        'password', 'token', 'api_key', 'secret', 'credential',
        'private_key', 'access_token', 'auth_token', 'api_secret',
        'password_hash', 'passphrase', 'credentials'
    ]

    for field in sensitive_fields:
        assert log_data[field] == '******', \
            f"Issue #1810 FALSE: {field} IS properly redacted to '******'"

    # Verify non-sensitive fields are preserved
    assert log_data['username'] == 'john_doe'
    assert log_data['email'] == 'john@example.com'
    assert log_data['user_id'] == 'user_123'

    # Final assertion
    assert True, \
        "Issue #1810 is CONFIRMED as a FALSE POSITIVE. " \
        "The sensitive field redaction functionality is FULLY IMPLEMENTED and WORKING CORRECTLY."

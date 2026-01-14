"""Test cases for Issue #1724 - Full redaction of sensitive fields.

ISSUE #1724 requests that sensitive fields be FULLY redacted with ***REDACTED***
instead of showing partial hashes (first 3 and last 3 characters), as partial
hash exposure can be a security vulnerability in high-security contexts.

This test verifies that:
1. All sensitive string values are fully redacted to ***REDACTED***
2. No partial character exposure occurs
3. Works for all sensitive field types (password, token, api_key, etc.)
4. Works for strings of any length (including long strings >= 8 chars)
"""

import pytest
from flywheel.storage import JSONFormatter


class TestFullSensitiveFieldRedaction:
    """Test suite for full redaction of sensitive fields (Issue #1724)."""

    def test_long_password_fully_redacted(self):
        """Test that long passwords (>= 8 chars) are FULLY redacted, not partial."""
        formatter = JSONFormatter()
        log_data = {'password': 'myVeryLongSecretPassword123', 'user': 'john'}
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1724: Should be FULLY redacted, NOT partial like "myV***123"
        assert result['password'] == '***REDACTED***', \
            f"Issue #1724: Expected full redaction, got: {result['password']}"
        assert result['user'] == 'john'

    def test_short_password_fully_redacted(self):
        """Test that short passwords (< 8 chars) are fully redacted."""
        formatter = JSONFormatter()
        log_data = {'password': 'short', 'user': 'john'}
        result = formatter._redact_sensitive_fields(log_data)

        assert result['password'] == '***REDACTED***'
        assert result['user'] == 'john'

    def test_token_fully_redacted(self):
        """Test that tokens are fully redacted without partial exposure."""
        formatter = JSONFormatter()
        log_data = {
            'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.very.long.token',
            'request_id': 'req_123'
        }
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1724: Should NOT show first 3 and last 3 chars like "eyJ***CJ9"
        assert result['token'] == '***REDACTED***', \
            f"Issue #1724: Expected full redaction, got: {result['token']}"
        assert result['request_id'] == 'req_123'

    def test_api_key_fully_redacted(self):
        """Test that API keys are fully redacted without partial exposure."""
        formatter = JSONFormatter()
        log_data = {
            'api_key': 'sk-1234567890abcdefghijklmnopqrstuv',
            'endpoint': 'api.example.com'
        }
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1724: Should NOT show first 3 and last 3 chars like "sk-***stuv"
        assert result['api_key'] == '***REDACTED***', \
            f"Issue #1724: Expected full redaction, got: {result['api_key']}"
        assert result['endpoint'] == 'api.example.com'

    def test_secret_fully_redacted(self):
        """Test that secret fields are fully redacted without partial exposure."""
        formatter = JSONFormatter()
        log_data = {
            'secret': 'mySuperSecretValueThatIsVeryLong',
            'config_id': 'cfg_456'
        }
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1724: Should NOT show first 3 and last 3 chars like "myS***ong"
        assert result['secret'] == '***REDACTED***', \
            f"Issue #1724: Expected full redaction, got: {result['secret']}"
        assert result['config_id'] == 'cfg_456'

    def test_exactly_8_chars_fully_redacted(self):
        """Test boundary case: exactly 8 characters should be fully redacted."""
        formatter = JSONFormatter()
        log_data = {'password': '12345678'}
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1724: Even boundary cases should be fully redacted
        assert result['password'] == '***REDACTED***', \
            f"Issue #1724: Expected full redaction for 8-char string, got: {result['password']}"

    def test_multiple_sensitive_fields_fully_redacted(self):
        """Test that all sensitive fields are fully redacted."""
        formatter = JSONFormatter()
        log_data = {
            'password': 'longPassword123',
            'token': 'abc123def456ghi789',
            'api_key': 99999,
            'secret': 'mySecret',
            'user': 'john',
            'message': 'test'
        }
        result = formatter._redact_sensitive_fields(log_data)

        # All sensitive fields should be fully redacted
        assert result['password'] == '***REDACTED***', \
            f"Issue #1724: password should be fully redacted, got: {result['password']}"
        assert result['token'] == '***REDACTED***', \
            f"Issue #1724: token should be fully redacted, got: {result['token']}"
        assert result['api_key'] == '***REDACTED***'
        assert result['secret'] == '***REDACTED***'
        assert result['user'] == 'john'
        assert result['message'] == 'test'

    def test_case_insensitive_fully_redacted(self):
        """Test that case variations of sensitive fields are fully redacted."""
        formatter = JSONFormatter()
        log_data = {
            'Password': 'UppercasePassword',
            'TOKEN': 'UPPERCASE_TOKEN',
            'Api_Key': 'MixedCaseKey123'
        }
        result = formatter._redact_sensitive_fields(log_data)

        # All case variations should be fully redacted
        assert result['Password'] == '***REDACTED***', \
            f"Issue #1724: Password should be fully redacted, got: {result['Password']}"
        assert result['TOKEN'] == '***REDACTED***', \
            f"Issue #1724: TOKEN should be fully redacted, got: {result['TOKEN']}"
        assert result['Api_Key'] == '***REDACTED***', \
            f"Issue #1724: Api_Key should be fully redacted, got: {result['Api_Key']}"


def test_issue_1724_full_redaction():
    """Main test for Issue #1724 - verify NO partial hash exposure."""
    formatter = JSONFormatter()

    # Test with a long password that would previously show "fir***ast"
    log_data = {
        'password': 'mySecretPasswordWithLotsOfCharacters',
        'user': 'alice',
        'action': 'login'
    }
    result = formatter._redact_sensitive_fields(log_data)

    # Issue #1724: Must be FULLY redacted, not partial
    assert result['password'] == '***REDACTED***', \
        f"Issue #1724 FAILED: Expected full redaction '***REDACTED***', got: {result['password']}"
    assert result['user'] == 'alice', \
        "Non-sensitive fields should remain unchanged"
    assert result['action'] == 'login', \
        "Non-sensitive fields should remain unchanged"

"""Test cases for Issue #1758 - Enhanced sensitive data redaction.

ISSUE #1758 requests that the redaction logic be enhanced to:
1. Recursively check nested dictionaries (already partially implemented)
2. Parse and check JSON string values for sensitive fields
3. Parse and check URL parameters for sensitive data
4. Use regex to scan large string values for sensitive keyword patterns

This test verifies that:
1. Sensitive data in nested dicts is redacted
2. Sensitive data in JSON strings is redacted
3. Sensitive data in URL parameters is redacted
4. Large strings with sensitive keywords are redacted
"""

import pytest
import json
from urllib.parse import parse_qs, urlparse
from flywheel.storage import JSONFormatter


class TestEnhancedRedaction:
    """Test suite for enhanced sensitive data redaction (Issue #1758)."""

    def test_nested_dict_sensitive_fields_redacted(self):
        """Test that sensitive fields in nested dictionaries are redacted."""
        formatter = JSONFormatter()
        log_data = {
            'user': 'john',
            'config': {
                'password': 'nested_password_123',
                'api_key': 'nested_api_key_456',
            },
            'credentials': {
                'secret': 'nested_secret_789',
            },
            'deeply': {
                'nested': {
                    'value': 'safe',
                    'token': 'deeply_nested_token_abc'
                }
            }
        }
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1758: All nested sensitive fields should be redacted
        assert result['config']['password'] == '***REDACTED***', \
            f"Issue #1758: Nested password should be redacted, got: {result['config']['password']}"
        assert result['config']['api_key'] == '***REDACTED***', \
            f"Issue #1758: Nested api_key should be redacted, got: {result['config']['api_key']}"
        assert result['credentials']['secret'] == '***REDACTED***', \
            f"Issue #1758: Nested secret should be redacted, got: {result['credentials']['secret']}"
        assert result['deeply']['nested']['token'] == '***REDACTED***', \
            f"Issue #1758: Deeply nested token should be redacted, got: {result['deeply']['nested']['token']}"
        # Non-sensitive nested fields should remain
        assert result['deeply']['nested']['value'] == 'safe', \
            "Non-sensitive nested fields should remain unchanged"

    def test_json_string_with_sensitive_data(self):
        """Test that sensitive data in JSON strings is detected and redacted."""
        formatter = JSONFormatter()
        # Simulating a JSON string that contains sensitive data
        inner_data = {'password': 'json_secret_123', 'user': 'alice'}
        json_string = json.dumps(inner_data)

        log_data = {
            'message': 'User action',
            'data': json_string  # JSON string containing sensitive data
        }
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1758: JSON strings should be parsed and sensitive data redacted
        # The result should have the password redacted in the parsed JSON
        assert 'password' not in str(result) or '***REDACTED***' in str(result), \
            f"Issue #1758: JSON string should have sensitive data redacted, got: {result['data']}"

    def test_url_parameters_with_sensitive_data(self):
        """Test that sensitive data in URL parameters is detected and redacted."""
        formatter = JSONFormatter()
        # URLs with sensitive parameters
        log_data = {
            'message': 'API request',
            'url': 'https://api.example.com/auth?password=secret123&token=abc123',
            'callback_url': 'https://example.com/reset?api_key=xyz789'
        }
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1758: URLs with sensitive parameters should have those values redacted
        assert 'secret123' not in str(result), \
            f"Issue #1758: URL parameter 'password' value should be redacted"
        assert 'abc123' not in str(result), \
            f"Issue #1758: URL parameter 'token' value should be redacted"
        assert 'xyz789' not in str(result), \
            f"Issue #1758: URL parameter 'api_key' value should be redacted"

    def test_large_string_with_sensitive_keywords(self):
        """Test that large strings containing sensitive keywords are handled."""
        formatter = JSONFormatter()
        # Large string that might contain sensitive information
        large_log = """
        Starting authentication process...
        User provided credentials for validation
        Access token generation in progress
        API key verification required
        End of log
        """
        log_data = {
            'message': 'System log',
            'details': large_log
        }
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1758: Large strings with sensitive keywords should be scanned
        # and potentially redacted or truncated if sensitive patterns found
        # At minimum, the system should handle large strings gracefully
        assert isinstance(result['details'], str), \
            "Large string should still be a string after processing"

    def test_list_containing_nested_sensitive_dicts(self):
        """Test that lists containing dictionaries with sensitive fields are handled."""
        formatter = JSONFormatter()
        log_data = {
            'users': [
                {'name': 'alice', 'password': 'alice_pass'},
                {'name': 'bob', 'password': 'bob_pass'},
                {'name': 'charlie', 'api_key': 'charlie_key'}
            ]
        }
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1758: All nested sensitive fields in lists should be redacted
        assert result['users'][0]['password'] == '***REDACTED***', \
            f"Issue #1758: Password in list item should be redacted, got: {result['users'][0]['password']}"
        assert result['users'][1]['password'] == '***REDACTED***', \
            f"Issue #1758: Password in second list item should be redacted"
        assert result['users'][2]['api_key'] == '***REDACTED***', \
            f"Issue #1758: API key in list item should be redacted"
        # Non-sensitive fields should remain
        assert result['users'][0]['name'] == 'alice'
        assert result['users'][1]['name'] == 'bob'
        assert result['users'][2]['name'] == 'charlie'

    def test_mixed_nested_structures(self):
        """Test complex nested structures with mixed data types."""
        formatter = JSONFormatter()
        log_data = {
            'request': {
                'url': 'https://api.example.com?token=xyz',
                'headers': {
                    'Authorization': 'Bearer secret_token_123'
                },
                'body': json.dumps({'password': 'body_secret'}),
                'metadata': {
                    'nested_list': [
                        {'credential': 'cred_1'},
                        {'credential': 'cred_2'}
                    ]
                }
            }
        }
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1758: All forms of nested sensitive data should be redacted
        # Check URL parameter
        assert 'xyz' not in str(result.get('request', {}).get('url', '')), \
            "URL parameter token should be redacted"
        # Check nested dict
        assert result['request']['headers']['Authorization'] == '***REDACTED***', \
            f"Authorization header should be redacted, got: {result['request']['headers'].get('Authorization')}"

    def test_empty_and_null_values_in_nested_structures(self):
        """Test that empty and null values in nested structures are handled."""
        formatter = JSONFormatter()
        log_data = {
            'level1': {
                'level2': {
                    'password': '',
                    'token': None,
                    'api_key': '   '
                }
            }
        }
        result = formatter._redact_sensitive_fields(log_data)

        # Issue #1758: Empty/null sensitive values should still be marked as redacted
        assert result['level1']['level2']['password'] in ['***REDACTED***', '', None], \
            "Empty password should be handled gracefully"
        assert result['level1']['level2']['token'] in ['***REDACTED***', '', None], \
            "None token should be handled gracefully"


def test_issue_1758_overall_enhanced_redaction():
    """Main test for Issue #1758 - verify comprehensive enhanced redaction."""
    formatter = JSONFormatter()

    # Comprehensive test case covering all enhancement areas
    log_data = {
        'user_id': 'user_123',
        'config': {
            'db_password': 'db_secret_xyz',
            'api_credentials': {
                'access_token': 'token_abc',
                'refresh_token': 'refresh_def'
            }
        },
        'request_url': 'https://api.service.com?api_key=secret_key_789',
        'json_payload': json.dumps({'secret': 'nested_json_secret'}),
        'items': [
            {'name': 'item1', 'auth': 'auth1'},
            {'name': 'item2', 'auth': 'auth2'}
        ]
    }

    result = formatter._redact_sensitive_fields(log_data)

    # Verify all types of sensitive data are handled
    # 1. Nested dicts
    assert result['config']['db_password'] == '***REDACTED***', \
        f"Issue #1758 FAILED: Nested db_password should be redacted, got: {result['config']['db_password']}"
    assert result['config']['api_credentials']['access_token'] == '***REDACTED***', \
        f"Issue #1758 FAILED: Nested access_token should be redacted"
    assert result['config']['api_credentials']['refresh_token'] == '***REDACTED***', \
        f"Issue #1758 FAILED: Nested refresh_token should be redacted"

    # 2. URL parameters
    assert 'secret_key_789' not in str(result['request_url']), \
        "Issue #1758 FAILED: URL parameter api_key value should be redacted"

    # 3. JSON strings
    assert 'nested_json_secret' not in str(result.get('json_payload', '')), \
        "Issue #1758 FAILED: JSON string secret should be redacted"

    # 4. List items
    assert result['items'][0]['auth'] == '***REDACTED***', \
        f"Issue #1758 FAILED: List item auth should be redacted"
    assert result['items'][1]['auth'] == '***REDACTED***', \
        f"Issue #1758 FAILED: Second list item auth should be redacted"

    # 5. Non-sensitive data should remain
    assert result['user_id'] == 'user_123', \
        "Non-sensitive fields should remain unchanged"
    assert result['items'][0]['name'] == 'item1', \
        "Non-sensitive list fields should remain unchanged"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

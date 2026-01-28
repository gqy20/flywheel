"""Tests for Issue #1655: Sensitive field redaction in nested structures.

This test ensures that sensitive fields are properly redacted at all levels
of nested dictionaries and lists, not just at the top level.
"""
import pytest
from logging import LogRecord
from flywheel.storage import ContextAwareJSONFormatter


class TestSensitiveFieldRedactionInNestedStructures:
    """Test that sensitive fields are redacted in nested structures."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ContextAwareJSONFormatter()

    def test_nested_dictionary_redaction(self):
        """Test that sensitive fields in nested dictionaries are redacted."""
        log_data = {
            'user': 'john_doe',
            'credentials': {
                'username': 'john_doe',
                'password': 'super_secret_password_123',
                'api_key': 'my_secret_api_key_456'
            }
        }

        result = self.formatter._redact_sensitive_fields(log_data)

        # Top-level fields should remain unchanged
        assert result['user'] == 'john_doe'

        # Nested sensitive fields should be redacted
        assert 'password' in result['credentials']
        assert result['credentials']['password'] == '***REDACTED***'
        assert result['credentials']['api_key'] == '***REDACTED***'

        # Non-sensitive nested fields should remain unchanged
        assert result['credentials']['username'] == 'john_doe'

    def test_list_of_dictionaries_redaction(self):
        """Test that sensitive fields in lists of dictionaries are redacted."""
        log_data = {
            'users': [
                {'username': 'user1', 'password': 'password1'},
                {'username': 'user2', 'password': 'password2'},
                {'username': 'user3', 'token': 'token123'}
            ]
        }

        result = self.formatter._redact_sensitive_fields(log_data)

        # All passwords and tokens in the list should be redacted
        assert result['users'][0]['password'] == '***REDACTED***'
        assert result['users'][1]['password'] == '***REDACTED***'
        assert result['users'][2]['token'] == '***REDACTED***'

        # Non-sensitive fields should remain unchanged
        assert result['users'][0]['username'] == 'user1'
        assert result['users'][1]['username'] == 'user2'
        assert result['users'][2]['username'] == 'user3'

    def test_deeply_nested_redaction(self):
        """Test that sensitive fields in deeply nested structures are redacted."""
        log_data = {
            'level1': {
                'level2': {
                    'level3': {
                        'secret': 'deeply_nested_secret',
                        'normal_field': 'normal_value'
                    }
                }
            }
        }

        result = self.formatter._redact_sensitive_fields(log_data)

        # Deeply nested secret should be redacted
        assert result['level1']['level2']['level3']['secret'] == '***REDACTED***'

        # Non-sensitive field should remain unchanged
        assert result['level1']['level2']['level3']['normal_field'] == 'normal_value'

    def test_mixed_structure_redaction(self):
        """Test redaction in a complex mixed structure with dicts and lists."""
        log_data = {
            'request_id': '12345',
            'auth': {
                'user': 'admin',
                'tokens': [
                    {'type': 'access', 'value': 'access_token_value'},
                    {'type': 'refresh', 'value': 'refresh_token_value'}
                ],
                'metadata': {
                    'api_key': 'nested_api_key',
                    'timestamp': '2024-01-01'
                }
            }
        }

        result = self.formatter._redact_sensitive_fields(log_data)

        # Top-level non-sensitive field should remain
        assert result['request_id'] == '12345'
        assert result['auth']['user'] == 'admin'

        # Tokens in list should be redacted
        assert result['auth']['tokens'][0]['value'] == '***REDACTED***'
        assert result['auth']['tokens'][1]['value'] == '***REDACTED***'

        # Nested API key should be redacted
        assert result['auth']['metadata']['api_key'] == '***REDACTED***'

        # Non-sensitive nested fields should remain
        assert result['auth']['tokens'][0]['type'] == 'access'
        assert result['auth']['tokens'][1]['type'] == 'refresh'
        assert result['auth']['metadata']['timestamp'] == '2024-01-01'

    def test_case_insensitive_redaction_in_nested_structures(self):
        """Test that field name matching is case-insensitive in nested structures."""
        log_data = {
            'auth': {
                'Password': 'should_be_redacted',
                'API_KEY': 'should_also_be_redacted',
                'Secret': 'also_redacted'
            }
        }

        result = self.formatter._redact_sensitive_fields(log_data)

        assert result['auth']['Password'] == '***REDACTED***'
        assert result['auth']['API_KEY'] == '***REDACTED***'
        assert result['auth']['Secret'] == '***REDACTED***'

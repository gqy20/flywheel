"""Test for Issue #1687: Complete JSONFormatter sensitive field redaction logic

This test ensures that:
1. Sensitive fields in nested dictionaries are properly redacted
2. Sensitive fields in nested lists are properly redacted
3. The recursive _redact_sensitive_fields_recursive method works correctly
4. Complex nested structures (dicts containing lists containing dicts) are handled
"""
import pytest
import logging
import json
from io import StringIO
from flywheel.storage import JSONFormatter


class TestNestedSensitiveFieldsRedaction:
    """Test complete recursive redaction of sensitive fields in nested structures."""

    def test_nested_dict_with_sensitive_fields(self):
        """Test that sensitive fields in nested dictionaries are redacted."""
        formatter = JSONFormatter()

        # Create a log record with nested sensitive data
        log_record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Add nested data with sensitive fields
        log_record.config = {
            'database': {
                'host': 'localhost',
                'password': 'secret_password_123',  # Should be redacted
                'api_key': 'nested_api_key_456',    # Should be redacted
            },
            'credentials': {
                'secret': 'nested_secret_789',      # Should be redacted
                'token': 'nested_token_abc',        # Should be redacted
            }
        }

        # Format the record
        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)

        # Verify top-level structure exists
        assert 'config' in log_data
        assert 'database' in log_data['config']
        assert 'credentials' in log_data['config']

        # Verify sensitive fields in nested dicts are redacted
        db_config = log_data['config']['database']
        assert db_config['host'] == 'localhost'  # Non-sensitive should not change
        assert db_config['password'] != 'secret_password_123'  # Should be redacted
        assert '***' in db_config['password']  # Should contain redaction markers
        assert db_config['password'][:3] == 'sec'  # Should show first 3 chars
        assert db_config['password'][-3:] == '123'  # Should show last 3 chars

        assert db_config['api_key'] != 'nested_api_key_456'
        assert '***' in db_config['api_key']

        creds = log_data['config']['credentials']
        assert creds['secret'] != 'nested_secret_789'
        assert '***' in creds['secret']

        assert creds['token'] != 'nested_token_abc'
        assert '***' in creds['token']

    def test_nested_list_with_sensitive_fields(self):
        """Test that sensitive fields in lists of dictionaries are redacted."""
        formatter = JSONFormatter()

        log_record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Add list of items with sensitive fields
        log_record.users = [
            {'name': 'Alice', 'password': 'alice_pass_123'},
            {'name': 'Bob', 'password': 'bob_pass_456', 'api_key': 'bob_key_789'},
            {'name': 'Charlie', 'token': 'charlie_token_abc'}
        ]

        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)

        # Verify structure
        assert 'users' in log_data
        assert len(log_data['users']) == 3

        # Verify redaction in list items
        assert log_data['users'][0]['name'] == 'Alice'
        assert log_data['users'][0]['password'] != 'alice_pass_123'
        assert '***' in log_data['users'][0]['password']

        assert log_data['users'][1]['name'] == 'Bob'
        assert log_data['users'][1]['password'] != 'bob_pass_456'
        assert log_data['users'][1]['api_key'] != 'bob_key_789'
        assert '***' in log_data['users'][1]['api_key']

        assert log_data['users'][2]['name'] == 'Charlie'
        assert log_data['users'][2]['token'] != 'charlie_token_abc'
        assert '***' in log_data['users'][2]['token']

    def test_deeply_nested_structure(self):
        """Test deeply nested structures (dict -> list -> dict -> sensitive field)."""
        formatter = JSONFormatter()

        log_record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Deeply nested structure
        log_record.data = {
            'level1': {
                'level2': [
                    {
                        'level3': {
                            'password': 'deeply_nested_pass',
                            'normal_field': 'normal_value'
                        }
                    }
                ]
            }
        }

        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)

        # Verify deep redaction works
        assert log_data['data']['level1']['level2'][0]['level3']['normal_field'] == 'normal_value'
        assert log_data['data']['level1']['level2'][0]['level3']['password'] != 'deeply_nested_pass'
        assert '***' in log_data['data']['level1']['level2'][0]['level3']['password']

    def test_case_insensitive_sensitive_fields(self):
        """Test that sensitive field matching is case-insensitive in nested structures."""
        formatter = JSONFormatter()

        log_record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Mixed case field names
        log_record.config = {
            'Password': 'upper_case_pass',
            'PASSWORD': 'all_caps_pass',
            'PaSsWoRd': 'mixed_case_pass',
            'API_KEY': 'all_caps_key',
            'api_Key': 'mixed_case_key'
        }

        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)

        # All case variations should be redacted
        assert log_data['config']['Password'] != 'upper_case_pass'
        assert log_data['config']['PASSWORD'] != 'all_caps_pass'
        assert log_data['config']['PaSsWoRd'] != 'mixed_case_pass'
        assert log_data['config']['API_KEY'] != 'all_caps_key'
        assert log_data['config']['api_Key'] != 'mixed_case_key'

        # All should contain redaction markers
        for field in ['Password', 'PASSWORD', 'PaSsWoRd', 'API_KEY', 'api_Key']:
            assert '***' in log_data['config'][field], f"Field {field} should be redacted"

    def test_short_sensitive_values_in_nested_structures(self):
        """Test redaction of short sensitive values in nested structures."""
        formatter = JSONFormatter()

        log_record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Short values should be completely redacted
        log_record.config = {
            'nested': {
                'password': '123',
                'secret': 'abc',
                'token': 'x'
            }
        }

        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)

        # Short values should be redacted
        assert log_data['config']['nested']['password'] != '123'
        assert log_data['config']['nested']['secret'] != 'abc'
        assert log_data['config']['nested']['token'] != 'x'

    def test_non_string_sensitive_values(self):
        """Test redaction of non-string sensitive values in nested structures."""
        formatter = JSONFormatter()

        log_record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Non-string values should be redacted
        log_record.config = {
            'nested': {
                'password': 123456,  # Number
                'secret': None,      # None
                'token': True,       # Boolean
                'api_key': ['list', 'of', 'values']  # List
            }
        }

        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)

        # Non-string sensitive values should be redacted
        assert log_data['config']['nested']['password'] == '***REDACTED***'
        assert log_data['config']['nested']['secret'] == '***REDACTED***'
        assert log_data['config']['nested']['token'] == '***REDACTED***'
        assert log_data['config']['nested']['api_key'] == '***REDACTED***'

    def test_all_sensitive_fields_are_redacted(self):
        """Test that all fields in SENSITIVE_FIELDS are properly redacted."""
        formatter = JSONFormatter()

        log_record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Test all sensitive field types
        log_record.credentials = {
            'password': 'test_password_123',
            'token': 'test_token_456',
            'api_key': 'test_api_key_789',
            'secret': 'test_secret_abc',
            'credential': 'test_credential_def',
            'private_key': 'test_private_key_ghi',
            'access_token': 'test_access_token_jkl',
            'auth_token': 'test_auth_token_mno',
            'api_secret': 'test_api_secret_pqr',
            'password_hash': 'test_password_hash_stu',
            'passphrase': 'test_passphrase_vwx',
            'credentials': 'test_credentials_yz'
        }

        formatted = formatter.format(log_record)
        log_data = json.loads(formatted)

        # All sensitive fields should be redacted
        for field in ['password', 'token', 'api_key', 'secret', 'credential',
                      'private_key', 'access_token', 'auth_token', 'api_secret',
                      'password_hash', 'passphrase', 'credentials']:
            assert field in log_data['credentials']
            assert log_data['credentials'][field] != f'test_{field}_'.replace('_', '_')
            assert '***' in log_data['credentials'][field] or log_data['credentials'][field] == '***REDACTED***'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

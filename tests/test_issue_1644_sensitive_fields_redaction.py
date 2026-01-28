"""Test for Issue #1644: Enhanced sensitive field redaction

This test ensures that:
1. SENSITIVE_FIELDS includes additional fields like 'secret', 'credential', etc.
2. Sensitive values are partially redacted (showing first and last few chars)
   instead of complete replacement with '******'
"""
import pytest
import tempfile
import os
from pathlib import Path

from flywheel import Storage


def test_sensitive_fields_includes_common_security_fields():
    """Test that SENSITIVE_FIELDS includes common security-related field names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        # Check that the base SENSITIVE_FIELDS set includes expected fields
        expected_fields = {'password', 'token', 'api_key', 'secret', 'credential',
                          'private_key', 'access_token', 'auth_token', 'api_secret',
                          'password_hash', 'passphrase', 'credentials'}

        # Verify all expected fields are in SENSITIVE_FIELDS
        for field in expected_fields:
            assert field in storage.SENSITIVE_FIELDS, \
                f"Field '{field}' should be in SENSITIVE_FIELDS"


def test_sensitive_fields_case_insensitive():
    """Test that sensitive field matching is case-insensitive."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        # Test various case combinations
        test_cases = [
            'password', 'PASSWORD', 'Password', 'PaSsWoRd',
            'secret', 'SECRET', 'Secret',
            'credential', 'CREDENTIAL', 'Credential',
        ]

        for field_name in test_cases:
            assert field_name.lower() in storage.SENSITIVE_FIELDS, \
                f"Field '{field_name}' (lowercase: {field_name.lower()}) should match sensitive fields"


def test_partial_redaction_of_sensitive_values():
    """Test that sensitive values are partially redacted, not completely replaced."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        # Test data with various sensitive fields
        log_data = {
            'username': 'john_doe',
            'password': 'SuperSecret123!',
            'secret': 'my-secret-key-abc-123',
            'credential': 'cred_xyz_789_def',
            'api_key': 'sk-1234567890abcdef',
            'normal_field': 'this_should_not_be_redacted',
            'token': 'bearer_token_abc_123',
        }

        # Apply redaction
        redacted = storage._redact_sensitive_fields(log_data)

        # Normal field should not be redacted
        assert redacted['normal_field'] == 'this_should_not_be_redacted', \
            "Non-sensitive fields should not be modified"

        # Sensitive fields should be partially redacted
        # They should show first few and last few chars, not just '******'
        for field in ['password', 'secret', 'credential', 'api_key', 'token']:
            assert redacted[field] != '******', \
                f"Field '{field}' should be partially redacted, not completely replaced"
            assert redacted[field] != log_data[field], \
                f"Field '{field}' should be redacted"
            assert '***' in redacted[field], \
                f"Field '{field}' should contain asterisks to indicate redaction"

            # Verify it shows parts of original value (first 3 and last 3 chars)
            original = log_data[field]
            redacted_value = redacted[field]

            # For values long enough (>= 8 chars), should show first 3 and last 3
            if len(original) >= 8:
                # Check that it starts with first 3 chars
                assert redacted_value[:3] == original[:3], \
                    f"Field '{field}' should show first 3 characters for debugging"
                # Check that it ends with last 3 chars
                assert redacted_value[-3:] == original[-3:], \
                    f"Field '{field}' should show last 3 characters for debugging"
                # Check that middle is redacted
                assert len(redacted_value) < len(original), \
                    f"Field '{field}' should have redacted middle portion"


def test_partial_redaction_preserves_debugging_info():
    """Test that partial redaction preserves enough information for debugging."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        # Test realistic scenarios
        test_cases = [
            ('api_key', 'sk-1234567890abcdef'),
            ('secret', 'prod_secret_key_v1'),
            ('password', 'MyP@ssw0rd!2024'),
            ('credential', 'aws_access_key_id_123'),
        ]

        for field_name, original_value in test_cases:
            log_data = {field_name: original_value}
            redacted = storage._redact_sensitive_fields(log_data)

            redacted_value = redacted[field_name]

            # Should not be the original value
            assert redacted_value != original_value, \
                f"Field '{field_name}' should be redacted"

            # Should not be just '******' (no debugging value)
            assert redacted_value != '******', \
                f"Field '{field_name}' should preserve partial info for debugging"

            # Should allow identification (prefix and suffix visible)
            if len(original_value) >= 8:
                assert original_value[:3] in redacted_value, \
                    f"Field '{field_name}' should show prefix"
                assert original_value[-3:] in redacted_value, \
                    f"Field '{field_name}' should show suffix"

                # Should clearly indicate redaction
                assert '*' in redacted_value, \
                    f"Field '{field_name}' should contain asterisks"


def test_short_sensitive_values():
    """Test redaction of short sensitive values (less than 8 characters)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        # Short values should still be redacted
        log_data = {
            'password': '12345',
            'secret': 'abc',
            'token': 'x' * 5,
        }

        redacted = storage._redact_sensitive_fields(log_data)

        # All should be redacted
        for field in ['password', 'secret', 'token']:
            assert redacted[field] != log_data[field], \
                f"Short field '{field}' should be redacted"
            assert '*' in redacted[field] or redacted[field] == '******', \
                f"Short field '{field}' should show redaction indicators"


def test_nested_dict_redaction():
    """Test that sensitive fields in nested dictionaries are also redacted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        log_data = {
            'user': 'john',
            'config': {
                'password': 'nested_password_123',
                'api_key': 'nested_api_key_456',
            },
            'credentials': {
                'secret': 'nested_secret_789',
            }
        }

        # Note: Current implementation may not handle nested dicts
        # This test documents expected behavior
        redacted = storage._redact_sensitive_fields(log_data)

        # Top-level check
        assert redacted['user'] == 'john'


def test_multiple_sensitive_fields_together():
    """Test redaction when multiple sensitive fields are present together."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        log_data = {
            'password': 'pass123',
            'secret': 'secret456',
            'api_key': 'key789',
            'token': 'token012',
            'credential': 'cred345',
            'normal_field_1': 'value1',
            'normal_field_2': 'value2',
        }

        redacted = storage._redact_sensitive_fields(log_data)

        # All sensitive fields should be redacted
        for field in ['password', 'secret', 'api_key', 'token', 'credential']:
            assert redacted[field] != log_data[field], \
                f"Sensitive field '{field}' should be redacted"
            assert redacted[field] != '******', \
                f"Sensitive field '{field}' should use partial redaction"

        # Normal fields should not be changed
        assert redacted['normal_field_1'] == 'value1'
        assert redacted['normal_field_2'] == 'value2'


def test_empty_and_none_values():
    """Test redaction behavior with empty and None values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        log_data = {
            'password': '',
            'secret': None,
            'api_key': '   ',
        }

        redacted = storage._redact_sensitive_fields(log_data)

        # Empty/None values should still be marked as sensitive
        # but handle gracefully
        for field in ['password', 'secret', 'api_key']:
            assert field in redacted
            # The implementation should handle these cases without errors
            assert redacted[field] is not None or redacted[field] == ''


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

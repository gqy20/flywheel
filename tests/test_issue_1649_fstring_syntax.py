"""Test for Issue #1649: Verify f-string syntax is correct

This test ensures that the f-string for redacting sensitive values
has proper syntax with closing quotes and brackets.

The bug reported was:
    redacted[key] = f"{value[:3]}***{value[-3:]}

The correct syntax should be:
    redacted[key] = f"{value[:3]}***{value[-3:]}"

This test verifies the functionality works correctly.
"""
import pytest
import tempfile
from pathlib import Path

from flywheel import Storage


def test_fstring_syntax_in_redaction():
    """Test that the f-string syntax for redaction is correct and functional.

    This test verifies that the f-string at line 272 in storage.py
    has proper syntax: f"{value[:3]}***{value[-3:]}"
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        # Test with a value that should be redacted (>= 8 characters)
        log_data = {
            'password': 'mysecretkey123',
            'api_key': 'sk-1234567890abcdef',
            'secret': 'prod_secret_key_v1',
        }

        # Apply redaction
        redacted = storage._redact_sensitive_fields(log_data)

        # Verify the f-string format is correct:
        # Should show first 3 chars + '***' + last 3 chars
        assert redacted['password'] == 'mys***123', \
            f"Expected 'mys***123' but got '{redacted['password']}'"
        assert redacted['api_key'] == 'sk-***def', \
            f"Expected 'sk-***def' but got '{redacted['api_key']}'"
        assert redacted['secret'] == 'pro***v1', \
            f"Expected 'pro***v1' but got '{redacted['secret']}'"


def test_redaction_format_structure():
    """Test that redacted values follow the expected format structure.

    The format should be: {first_3_chars}***{last_3_chars}
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        test_cases = [
            ('password', 'SuperSecret123!', 'Sup***1!'),
            ('token', 'bearer_token_abc_123', 'bea***123'),
            ('api_key', 'sk-1234567890abcdef', 'sk-***def'),
        ]

        for field_name, original_value, expected_redacted in test_cases:
            log_data = {field_name: original_value}
            redacted = storage._redact_sensitive_fields(log_data)

            assert redacted[field_name] == expected_redacted, \
                f"Field '{field_name}': expected '{expected_redacted}' but got '{redacted[field_name]}'"

            # Verify the structure: exactly 3 asterisks in the middle
            redacted_value = redacted[field_name]
            assert '***' in redacted_value, \
                f"Redacted value should contain '***' in the middle"
            assert redacted_value.count('*') == 3, \
                f"Redacted value should contain exactly 3 asterisks"


def test_fstring_handles_edge_cases():
    """Test that the f-string handles edge cases correctly.

    This ensures the f-string syntax doesn't break with various input types.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        # Test with exactly 8 characters (boundary case)
        log_data = {'password': '12345678'}
        redacted = storage._redact_sensitive_fields(log_data)
        assert redacted['password'] == '123***678', \
            "Should handle 8-character value correctly"

        # Test with 9 characters
        log_data = {'password': '123456789'}
        redacted = storage._redact_sensitive_fields(log_data)
        assert redacted['password'] == '123***789', \
            "Should handle 9-character value correctly"

        # Test with very long value
        log_data = {'password': 'a' * 100}
        redacted = storage._redact_sensitive_fields(log_data)
        assert redacted['password'] == 'aaa***aaa', \
            "Should handle very long value correctly"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

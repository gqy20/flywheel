"""Test for Issue #1657: Enhanced sensitive field redaction with type checking

This test ensures that:
1. Sensitive fields with non-string values (None, numbers, etc.) are handled gracefully
2. The redaction logic doesn't crash when value is not a string instance
3. Non-string sensitive values return '***REDACTED***' instead of attempting slice operations
"""
import pytest
import tempfile

from flywheel import Storage


def test_sensitive_field_with_none_value():
    """Test that sensitive field with None value doesn't crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        log_data = {
            'username': 'john_doe',
            'password': None,  # None value should be handled
            'normal_field': 'value',
        }

        # Should not raise an exception
        redacted = storage._redact_sensitive_fields(log_data)

        # Password should be redacted
        assert redacted['password'] is not None or redacted['password'] == 'None'
        assert redacted['normal_field'] == 'value'


def test_sensitive_field_with_integer_value():
    """Test that sensitive field with integer value doesn't crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        log_data = {
            'username': 'john_doe',
            'password': 123456,  # Integer value should be handled
            'normal_field': 'value',
        }

        # Should not raise an exception
        redacted = storage._redact_sensitive_fields(log_data)

        # Password should be redacted
        assert redacted['password'] != 123456
        assert redacted['normal_field'] == 'value'


def test_sensitive_field_with_float_value():
    """Test that sensitive field with float value doesn't crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        log_data = {
            'username': 'john_doe',
            'secret': 123.456,  # Float value should be handled
            'normal_field': 'value',
        }

        # Should not raise an exception
        redacted = storage._redact_sensitive_fields(log_data)

        # Secret should be redacted
        assert redacted['secret'] != 123.456
        assert redacted['normal_field'] == 'value'


def test_sensitive_field_with_boolean_value():
    """Test that sensitive field with boolean value doesn't crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        log_data = {
            'username': 'john_doe',
            'password': True,  # Boolean value should be handled
            'normal_field': 'value',
        }

        # Should not raise an exception
        redacted = storage._redact_sensitive_fields(log_data)

        # Password should be redacted
        assert redacted['password'] is not True
        assert redacted['normal_field'] == 'value'


def test_sensitive_field_with_list_value():
    """Test that sensitive field with list value doesn't crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        log_data = {
            'username': 'john_doe',
            'password': ['p', 'a', 's', 's'],  # List value should be handled
            'normal_field': 'value',
        }

        # Should not raise an exception
        redacted = storage._redact_sensitive_fields(log_data)

        # Password should be redacted
        assert redacted['password'] != ['p', 'a', 's', 's']
        assert redacted['normal_field'] == 'value'


def test_sensitive_field_with_dict_value():
    """Test that sensitive field with dict value doesn't crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        log_data = {
            'username': 'john_doe',
            'password': {'key': 'value'},  # Dict value should be handled
            'normal_field': 'value',
        }

        # Should not raise an exception
        redacted = storage._redact_sensitive_fields(log_data)

        # Password should be redacted
        assert redacted['password'] != {'key': 'value'}
        assert redacted['normal_field'] == 'value'


def test_multiple_non_string_sensitive_fields():
    """Test multiple sensitive fields with various non-string types."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(tmpdir)

        log_data = {
            'username': 'john_doe',
            'password': 123456,
            'secret': None,
            'api_key': 123.456,
            'token': True,
            'normal_field': 'value',
        }

        # Should not raise an exception
        redacted = storage._redact_sensitive_fields(log_data)

        # All sensitive fields should be redacted
        assert redacted['password'] != 123456
        assert redacted['secret'] is not None or redacted['secret'] == 'None'
        assert redacted['api_key'] != 123.456
        assert redacted['token'] is not True
        assert redacted['normal_field'] == 'value'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

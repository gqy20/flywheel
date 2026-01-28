"""Tests for _get_stale_lock_timeout function (Issue #981)."""
import os
import pytest
from flywheel.storage import _get_stale_lock_timeout, _STALE_LOCK_TIMEOUT_DEFAULT


class TestGetStaleLockTimeout:
    """Test suite for _get_stale_lock_timeout function."""

    def test_returns_default_when_env_not_set(self):
        """Test that default timeout is returned when env var is not set."""
        # Ensure env var is not set
        if 'FW_LOCK_STALE_SECONDS' in os.environ:
            del os.environ['FW_LOCK_STALE_SECONDS']

        result = _get_stale_lock_timeout()
        assert result == _STALE_LOCK_TIMEOUT_DEFAULT
        assert isinstance(result, int)

    def test_returns_default_when_env_is_empty_string(self):
        """Test that default timeout is returned when env var is empty string."""
        os.environ['FW_LOCK_STALE_SECONDS'] = ''
        result = _get_stale_lock_timeout()
        assert result == _STALE_LOCK_TIMEOUT_DEFAULT
        assert isinstance(result, int)

    def test_returns_default_when_env_is_negative(self):
        """Test that default timeout is returned when env var is negative."""
        os.environ['FW_LOCK_STALE_SECONDS'] = '-100'
        result = _get_stale_lock_timeout()
        assert result == _STALE_LOCK_TIMEOUT_DEFAULT
        assert isinstance(result, int)

    def test_returns_default_when_env_is_zero(self):
        """Test that default timeout is returned when env var is zero."""
        os.environ['FW_LOCK_STALE_SECONDS'] = '0'
        result = _get_stale_lock_timeout()
        assert result == _STALE_LOCK_TIMEOUT_DEFAULT
        assert isinstance(result, int)

    def test_returns_custom_value_when_env_is_positive(self):
        """Test that custom timeout is returned when env var is positive."""
        os.environ['FW_LOCK_STALE_SECONDS'] = '600'
        result = _get_stale_lock_timeout()
        assert result == 600
        assert isinstance(result, int)

    def test_returns_custom_value_for_large_positive_number(self):
        """Test that custom timeout is returned for large positive numbers."""
        os.environ['FW_LOCK_STALE_SECONDS'] = '3600'
        result = _get_stale_lock_timeout()
        assert result == 3600
        assert isinstance(result, int)

    def test_returns_default_when_env_is_invalid_string(self):
        """Test that default timeout is returned when env var is not a valid integer."""
        os.environ['FW_LOCK_STALE_SECONDS'] = 'invalid'
        result = _get_stale_lock_timeout()
        assert result == _STALE_LOCK_TIMEOUT_DEFAULT
        assert isinstance(result, int)

    def test_returns_default_when_env_is_float_string(self):
        """Test that default timeout is returned when env var is a float string."""
        os.environ['FW_LOCK_STALE_SECONDS'] = '123.45'
        result = _get_stale_lock_timeout()
        assert result == _STALE_LOCK_TIMEOUT_DEFAULT
        assert isinstance(result, int)

    def test_function_never_returns_none(self):
        """Test that function never returns None for any input."""
        test_cases = [
            None,  # env var not set
            '',
            '0',
            '-1',
            '100',
            '9999',
            'invalid',
            '123.45',
        ]

        for env_value in test_cases:
            if env_value is None:
                if 'FW_LOCK_STALE_SECONDS' in os.environ:
                    del os.environ['FW_LOCK_STALE_SECONDS']
            else:
                os.environ['FW_LOCK_STALE_SECONDS'] = env_value

            result = _get_stale_lock_timeout()
            assert result is not None, f"Function returned None for env_value={env_value}"
            assert isinstance(result, int), f"Function returned {type(result)} instead of int for env_value={env_value}"

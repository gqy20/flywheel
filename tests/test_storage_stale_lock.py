"""Tests for stale lock timeout functionality (Issue #962)."""
import os
import pytest
from flywheel.storage import _get_stale_lock_timeout, _STALE_LOCK_TIMEOUT_DEFAULT


class TestStaleLockTimeout:
    """Test suite for _get_stale_lock_timeout function."""

    def test_returns_default_when_no_env_var(self):
        """Test that default timeout is returned when env var is not set."""
        # Ensure env var is not set
        if 'FW_LOCK_STALE_SECONDS' in os.environ:
            del os.environ['FW_LOCK_STALE_SECONDS']

        result = _get_stale_lock_timeout()
        assert result == _STALE_LOCK_TIMEOUT_DEFAULT
        assert result == 300

    def test_returns_custom_timeout_from_env(self):
        """Test that custom timeout is returned when env var is set."""
        os.environ['FW_LOCK_STALE_SECONDS'] = '600'
        result = _get_stale_lock_timeout()
        assert result == 600

    def test_returns_default_for_invalid_string(self):
        """Test that default timeout is returned for invalid string."""
        os.environ['FW_LOCK_STALE_SECONDS'] = 'not_a_number'
        result = _get_stale_lock_timeout()
        assert result == _STALE_LOCK_TIMEOUT_DEFAULT

    def test_returns_default_for_negative_value(self):
        """Test that default timeout is returned for negative value."""
        os.environ['FW_LOCK_STALE_SECONDS'] = '-100'
        result = _get_stale_lock_timeout()
        assert result == _STALE_LOCK_TIMEOUT_DEFAULT

    def test_returns_default_for_zero(self):
        """Test that default timeout is returned for zero."""
        os.environ['FW_LOCK_STALE_SECONDS'] = '0'
        result = _get_stale_lock_timeout()
        assert result == _STALE_LOCK_TIMEOUT_DEFAULT

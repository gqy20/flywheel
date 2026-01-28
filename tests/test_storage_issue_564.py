"""Tests for Issue #564 - Verify _get_file_lock_range_from_handle method is complete.

This test ensures the _get_file_lock_range_from_handle method has proper
implementation for both Windows and Unix platforms.
"""

import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest

# Import the storage module
from flywheel.storage import Storage


class TestGetFileLockRangeFromHandle:
    """Test suite for _get_file_lock_range_from_handle method (Issue #564)."""

    def test_method_exists(self):
        """Test that the method exists and can be called."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(tmpdir)
            # The method should exist and be callable
            assert hasattr(storage, '_get_file_lock_range_from_handle')
            assert callable(storage._get_file_lock_range_from_handle)

    def test_windows_returns_tuple(self):
        """Test that Windows branch returns (0, 1) tuple."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(tmpdir)
            with patch('os.name', 'nt'):
                result = storage._get_file_lock_range_from_handle(None)
                assert result == (0, 1), f"Expected (0, 1) but got {result}"
                assert isinstance(result, tuple)
                assert len(result) == 2
                assert result[0] == 0
                assert result[1] == 1

    def test_unix_returns_zero(self):
        """Test that Unix branch returns 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(tmpdir)
            with patch('os.name', 'posix'):
                result = storage._get_file_lock_range_from_handle(None)
                assert result == 0, f"Expected 0 but got {result}"
                assert isinstance(result, int)

    def test_windows_and_unix_branches_complete(self):
        """Test that both Windows and Unix branches are complete and return valid values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(tmpdir)

            # Test Windows branch
            with patch('os.name', 'nt'):
                try:
                    result = storage._get_file_lock_range_from_handle(None)
                    assert result == (0, 1), f"Windows branch incomplete or incorrect: {result}"
                except Exception as e:
                    pytest.fail(f"Windows branch raised exception: {e}")

            # Test Unix branch
            with patch('os.name', 'posix'):
                try:
                    result = storage._get_file_lock_range_from_handle(None)
                    assert result == 0, f"Unix branch incomplete or incorrect: {result}"
                except Exception as e:
                    pytest.fail(f"Unix branch raised exception: {e}")

    def test_current_platform(self):
        """Test that the method works correctly on the current platform."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(tmpdir)
            result = storage._get_file_lock_range_from_handle(None)

            if os.name == 'nt':
                assert result == (0, 1), f"Windows should return (0, 1) but got {result}"
            else:
                assert result == 0, f"Unix should return 0 but got {result}"

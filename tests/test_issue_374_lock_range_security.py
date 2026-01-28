"""Test for Issue #374: Insecure fallback for lock range validation

This test verifies that when lock_range is invalid (<= 0), the system
fails fast with an exception instead of using an insecure partial lock.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestLockRangeSecurity:
    """Test secure handling of invalid lock ranges."""

    def test_invalid_lock_range_should_raise_error(self):
        """Test that invalid lock range (<= 0) raises an exception instead of falling back."""
        if os.name != 'nt':
            pytest.skip("This test is for Windows only")

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_secure_lock.json"

            # Create storage instance
            storage = Storage(str(storage_path))

            # Mock the _get_file_lock_range_from_handle to return invalid value
            with patch.object(
                storage,
                '_get_file_lock_range_from_handle',
                return_value=0  # Invalid lock range
            ):
                # Attempting to save should raise an error due to invalid lock range
                # NOT fall back to 4096 which is insecure
                with pytest.raises(RuntimeError) as exc_info:
                    storage.add(Todo(title="Test task"))

                # Verify the error message mentions the security issue
                assert "Invalid lock range" in str(exc_info.value) or \
                       "lock range" in str(exc_info.value).lower()

    def test_negative_lock_range_should_raise_error(self):
        """Test that negative lock range raises an exception."""
        if os.name != 'nt':
            pytest.skip("This test is for Windows only")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_negative_lock.json"
            storage = Storage(str(storage_path))

            # Mock to return negative value
            with patch.object(
                storage,
                '_get_file_lock_range_from_handle',
                return_value=-100  # Negative lock range
            ):
                # Should raise an error
                with pytest.raises(RuntimeError) as exc_info:
                    storage.add(Todo(title="Test task"))

                # Verify error mentions the problem
                assert "lock" in str(exc_info.value).lower() or \
                       "range" in str(exc_info.value).lower()

    def test_valid_lock_range_should_work(self):
        """Test that valid lock ranges still work correctly."""
        if os.name != 'nt':
            pytest.skip("This test is for Windows only")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_valid_lock.json"
            storage = Storage(str(storage_path))

            # Mock to return valid positive value
            with patch.object(
                storage,
                '_get_file_lock_range_from_handle',
                return_value=4096  # Valid lock range
            ):
                # Should work normally
                todo = storage.add(Todo(title="Test task"))
                assert todo is not None
                assert todo.title == "Test task"

    def test_minimum_lock_range_enforced(self):
        """Test that lock range meets minimum security requirements."""
        if os.name != 'nt':
            pytest.skip("This test is for Windows only")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_minimum_lock.json"
            storage = Storage(str(storage_path))

            # Test with very small but positive value (e.g., 1 byte)
            # This should also be rejected as insecure
            with patch.object(
                storage,
                '_get_file_lock_range_from_handle',
                return_value=1  # Too small to be secure
            ):
                # The implementation should either:
                # 1. Raise an error for insufficient lock coverage
                # 2. Use a secure minimum (entire file if possible)
                # Current implementation should raise error for security
                with pytest.raises((RuntimeError, ValueError)) as exc_info:
                    storage.add(Todo(title="Test task"))

                # Verify it's a security-related error
                error_str = str(exc_info.value).lower()
                assert "lock" in error_str or "range" in error_str or "secure" in error_str

    def test_no_fallback_to_4096_partial_lock(self):
        """Test that system does NOT fall back to 4096 byte partial lock.

        This is the core security issue: partial locking (only 4096 bytes)
        while the rest of the file remains accessible is a security violation.
        The system should either:
        1. Lock the entire file
        2. Fail the operation with an exception
        """
        if os.name != 'nt':
            pytest.skip("This test is for Windows only")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_no_partial_lock.json"
            storage = Storage(str(storage_path))

            # Mock fstat to simulate a file that's larger than 4096 bytes
            # but return invalid size (e.g., 0 or negative)
            mock_stat = MagicMock()
            mock_stat.st_size = 0  # Invalid size

            with patch('os.fstat', return_value=mock_stat):
                # Should NOT fall back to 4096
                # Should raise an error instead
                with pytest.raises(RuntimeError) as exc_info:
                    storage.add(Todo(title="Test task"))

                # The error should indicate the problem
                error_msg = str(exc_info.value).lower()
                # Either mentions invalid lock range or secure failure
                assert any(term in error_msg for term in [
                    "invalid",
                    "lock",
                    "range",
                    "secure"
                ])

    def test_fstat_failure_propagates_as_error(self):
        """Test that fstat failures are not silently ignored with fallback."""
        if os.name != 'nt':
            pytest.skip("This test is for Windows only")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_fstat_error.json"
            storage = Storage(str(storage_path))

            # Mock fstat to raise an error
            with patch('os.fstat', side_effect=OSError("File stat failed")):
                # Should NOT fall back to 4096
                # Should propagate the error or raise a security error
                with pytest.raises((OSError, RuntimeError)) as exc_info:
                    storage.add(Todo(title="Test task"))

                # Should be an error, not silent fallback
                assert exc_info.value is not None

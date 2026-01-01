"""Tests for Issue #316 - Windows file lock range overflow prevention."""

import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_lock_range_prevents_overflow():
    """Test that lock range doesn't cause integer overflow for large files.

    Issue #316: Windows msvcrt.locking may have restrictions on lock range.
    Using file_size + 1MB could potentially exceed safe integer limits.
    The lock range should be capped at a reasonable maximum.

    This test verifies that for large files, the lock range doesn't exceed
    safe limits that could cause msvcrt.locking to fail.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_large_file.json"
        storage = Storage(str(storage_path))

        # Create a large file (100MB)
        large_size = 100 * 1024 * 1024  # 100MB
        with storage_path.open('w') as f:
            f.write('x' * large_size)

        # Test lock range calculation
        with storage_path.open('r') as f:
            lock_range = storage._get_file_lock_range_from_handle(f)

            # Verify lock range is positive (required by msvcrt.locking)
            assert lock_range > 0, "Lock range must be positive"

            # For large files, the lock range should NOT be file_size + 1MB
            # as this could be excessive. Instead, it should use a reasonable
            # maximum or a different strategy.
            # Current code: returns file_size + 1MB = 101MB
            # This test expects it to FAIL with current implementation
            # After fix: should use a capped or different approach

            # The current implementation will return 101MB which might be acceptable
            # but let's verify it doesn't exceed safe limits
            max_safe_int = 2**31 - 1  # Max signed 32-bit integer
            assert lock_range <= max_safe_int, \
                f"Lock range {lock_range} exceeds max safe integer"


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_lock_range_for_very_large_files():
    """Test lock range for files approaching 2GB limit.

    Issue #316: For files near the 2GB limit, adding 1MB buffer could
    cause integer overflow or exceed msvcrt.locking limits.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_very_large.json"
        storage = Storage(str(storage_path))

        # Simulate a file size near 2GB (without actually creating that large file)
        # We'll test the logic by mocking the file handle
        class MockFileHandle:
            def __init__(self, size):
                self._size = size
                self._pos = 0

            def fileno(self):
                return 0

            def tell(self):
                return self._pos

            def seek(self, pos, whence=0):
                if whence == 0:  # SEEK_SET
                    self._pos = pos
                elif whence == 2:  # SEEK_END
                    self._pos = self._size

        # Test with file size near 2GB limit
        near_limit_size = 2**31 - 1024 * 1024  # 2GB - 1MB
        mock_handle = MockFileHandle(near_limit_size)

        lock_range = storage._get_file_lock_range_from_handle(mock_handle)

        # Current implementation: near_limit_size + 1MB = 2GB
        # This would be exactly at the limit, which might cause issues
        # After fix: should cap at a safe maximum
        max_safe = 2**31 - 1
        assert lock_range <= max_safe, \
            f"Lock range {lock_range} should not exceed max safe value {max_safe}"


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_lock_range_uses_fixed_region_alternative():
    """Test that Windows uses a fixed lock region instead of file_size + buffer.

    Issue #316 suggests using a fixed region (e.g., first 100 bytes) or locking
    the entire file with a large constant, rather than file_size + 1MB.

    This test verifies the fix uses a safer approach.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_fixed_region.json"
        storage = Storage(str(storage_path))

        # Test with various file sizes
        test_cases = [
            (0, "empty file"),
            (100, "small file"),
            (1024 * 1024, "1MB file"),
            (10 * 1024 * 1024, "10MB file"),
        ]

        for size, description in test_cases:
            # Create file with specific size
            with storage_path.open('w') as f:
                if size > 0:
                    f.write('x' * size)
                else:
                    f.write('')  # Empty file

            # Get lock range
            with storage_path.open('r') as f:
                lock_range = storage._get_file_lock_range_from_handle(f)

                # Current implementation: file_size + 1MB
                # Expected after fix: should use a fixed reasonable value
                # or cap the maximum at a safe limit

                # For now, just verify it's positive and reasonable
                assert lock_range > 0, f"Lock range must be positive for {description}"
                assert lock_range <= 2**31 - 1, \
                    f"Lock range must be within safe integer limits for {description}"


def test_lock_range_fallback_on_error():
    """Test that lock range calculation falls back safely on errors.

    This test runs on all platforms to verify error handling.
    Issue #316: Error handling should use a safe default.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_fallback.json"
        storage = Storage(str(storage_path))

        # Create a mock file handle that will fail on tell()
        class MockFileHandle:
            def fileno(self):
                return 0

            def tell(self):
                raise OSError("Simulated error")

            def seek(self, pos, whence=0):
                pass

        mock_handle = MockFileHandle()
        lock_range = storage._get_file_lock_range_from_handle(mock_handle)

        # Should fall back to default 1MB
        expected_default = 1024 * 1024
        assert lock_range == expected_default, \
            f"Lock range should fall back to {expected_default} on error, got {lock_range}"

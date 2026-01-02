"""Test for Issue #480 - Windows file lock range calculation.

This test verifies that the Windows file lock range correctly represents
4GB (0x100000000 bytes) instead of 4GB-1 (0xFFFFFFFF bytes).
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from flywheel.storage import Storage


class TestWindowsLockRangeCalculation:
    """Test Windows file lock range calculation (Issue #480)."""

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_windows_lock_range_is_exactly_4gb(self):
        """Test that Windows lock range represents exactly 4GB (0x100000000).

        The lock range should be (0, 1) which represents:
        0 + 1 << 32 = 0x100000000 = exactly 4GB

        NOT (0xFFFFFFFF, 0) which represents:
        0xFFFFFFFF + 0 << 32 = 0xFFFFFFFF = 4GB - 1 byte
        """
        # Create a temporary storage instance
        with patch('flywheel.storage.Storage._create_and_secure_directories'):
            with patch('flywheel.storage.Storage._secure_all_parent_directories'):
                with patch('flywheel.storage.Storage._load'):
                    storage = Storage(path="/tmp/test_todos_480.json")

                    # Get the lock range
                    lock_range = storage._get_file_lock_range_from_handle(None)

                    # Verify it represents exactly 4GB
                    low, high = lock_range

                    # Calculate the actual range in bytes
                    actual_range = low + (high << 32)

                    # Expected: 4GB = 0x100000000 = 4294967296 bytes
                    expected_range = 0x100000000  # 4GB

                    assert actual_range == expected_range, (
                        f"Lock range should be exactly 4GB (0x100000000 bytes), "
                        f"but got {actual_range} (0x{actual_range:X}) bytes. "
                        f"Current values: low={low} (0x{low:X}), high={high} (0x{high:X})"
                    )

                    # Verify the correct low/high values
                    assert low == 0, f"Low value should be 0, got {low}"
                    assert high == 1, f"High value should be 1, got {high}"

    def test_windows_lock_range_calculation_mock(self):
        """Test lock range calculation using mock for non-Windows platforms."""
        # Mock Windows environment
        with patch('os.name', 'nt'):
            with patch('flywheel.storage.win32file', create=True):
                with patch('flywheel.storage.win32con', create=True):
                    with patch('flywheel.storage.pywintypes', create=True):
                        # Mock the Storage constructor to avoid actual initialization
                        with patch('flywheel.storage.Storage._create_and_secure_directories'):
                            with patch('flywheel.storage.Storage._secure_all_parent_directories'):
                                with patch('flywheel.storage.Storage._load'):
                                    storage = Storage(path="/tmp/test_todos_480_mock.json")

                                    # Get the lock range
                                    lock_range = storage._get_file_lock_range_from_handle(None)

                                    # Verify it represents exactly 4GB
                                    low, high = lock_range
                                    actual_range = low + (high << 32)
                                    expected_range = 0x100000000  # 4GB

                                    assert actual_range == expected_range, (
                                        f"Lock range should be exactly 4GB, "
                                        f"but got {actual_range} bytes"
                                    )

                                    assert low == 0, f"Low value should be 0, got {low}"
                                    assert high == 1, f"High value should be 1, got {high}"

"""Tests for Issue #484 - Windows file lock range calculation verification.

Issue #484 claims that the Windows file lock range calculation (0, 1) is incorrect.
This test verifies that the current implementation is ACTUALLY CORRECT.

The issue reporter misunderstood the Windows LockFileEx API. They thought (0, 1)
might mean "lock 1 byte at offset 0", but the API actually interprets these as:
- nNumberOfBytesToLockLow = 0
- nNumberOfBytesToLockHigh = 1

Which together represent a 64-bit length: 0 + (1 << 32) = 4GB.

References:
- Windows LockFileEx documentation: https://docs.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex
- Issue #480 already corrected this to use (0, 1) for exactly 4GB
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import Storage


class TestWindowsFileLockRangeIssue484:
    """Test Windows file lock range calculation - verifying Issue #484 is actually correct."""

    def test_windows_lock_range_calculation_is_correct(self):
        """Test that (0, 1) correctly represents 4GB, not 1 byte.

        This test refutes the claim in Issue #484. The lock range (0, 1)
        represents 4GB, not 1 byte as the issue reporter believed.

        Windows LockFileEx API:
        - nNumberOfBytesToLockLow: The low-order 32 bits of the length
        - nNumberOfBytesToLockHigh: The high-order 32 bits of the length
        - Total length = nNumberOfBytesToLockLow + (nNumberOfBytesToLockHigh << 32)

        For (0, 1):
        - Total = 0 + (1 << 32) = 4294967296 bytes = 4GB

        This is CORRECT. The issue reporter misunderstood the API.
        """
        # Mock to allow testing on any platform
        with patch('os.name', 'nt'):
            with patch('flywheel.storage.win32file', create=True):
                with patch('flywheel.storage.win32con', create=True):
                    with patch('flywheel.storage.pywintypes', create=True):
                        with patch('flywheel.storage.Storage._create_and_secure_directories'):
                            with patch('flywheel.storage.Storage._secure_all_parent_directories'):
                                with patch('flywheel.storage.Storage._load'):
                                    storage = Storage(path="/tmp/test_issue_484.json")

                                    # Get the lock range
                                    lock_range = storage._get_file_lock_range_from_handle(None)

                                    # Verify structure
                                    assert isinstance(lock_range, tuple)
                                    assert len(lock_range) == 2

                                    low, high = lock_range

                                    # Calculate the 64-bit range as Windows API interprets it
                                    actual_range = low + (high << 32)

                                    # 4GB = 0x100000000 = 4294967296 bytes
                                    expected_range = 4 * 1024 * 1024 * 1024  # 4GB

                                    # Verify it represents 4GB, not 1 byte
                                    assert actual_range == expected_range, (
                                        f"Issue #484 is INCORRECT. Lock range {lock_range} "
                                        f"represents {actual_range} bytes (4GB), not 1 byte. "
                                        f"Calculation: {low} + ({high} << 32) = {actual_range}"
                                    )

                                    # Verify individual values
                                    assert low == 0, f"Low value should be 0 for 4GB, got {low}"
                                    assert high == 1, f"High value should be 1 for 4GB, got {high}"

    def test_windows_lock_range_is_not_1_byte(self):
        """Explicitly test that the lock range is NOT 1 byte.

        This directly addresses the misunderstanding in Issue #484.
        """
        with patch('os.name', 'nt'):
            with patch('flywheel.storage.win32file', create=True):
                with patch('flywheel.storage.win32con', create=True):
                    with patch('flywheel.storage.pywintypes', create=True):
                        with patch('flywheel.storage.Storage._create_and_secure_directories'):
                            with patch('flywheel.storage.Storage._secure_all_parent_directories'):
                                with patch('flywheel.storage.Storage._load'):
                                    storage = Storage(path="/tmp/test_issue_484_verify.json")
                                    lock_range = storage._get_file_lock_range_from_handle(None)

                                    low, high = lock_range
                                    actual_range = low + (high << 32)

                                    # Verify it's NOT 1 byte
                                    assert actual_range != 1, (
                                        f"Lock range should NOT be 1 byte. "
                                        f"Actual range: {actual_range} bytes (4GB)"
                                    )

                                    # Verify it's a large range (at least 1GB)
                                    min_acceptable = 1024 * 1024 * 1024  # 1GB
                                    assert actual_range >= min_acceptable, (
                                        f"Lock range is too small. "
                                        f"Expected at least 1GB, got {actual_range} bytes"
                                    )

    def test_unix_lock_range_returns_zero(self):
        """Test that Unix lock range returns 0 (ignored by fcntl.flock)."""
        with patch('os.name', 'posix'):
            with patch('flywheel.storage.fcntl', create=True):
                with patch('flywheel.storage.Storage._create_and_secure_directories'):
                    with patch('flywheel.storage.Storage._secure_all_parent_directories'):
                        with patch('flywheel.storage.Storage._load'):
                            storage = Storage(path="/tmp/test_issue_484_unix.json")
                            lock_range = storage._get_file_lock_range_from_handle(None)

                            assert lock_range == 0, f"Unix lock range should be 0, got {lock_range}"

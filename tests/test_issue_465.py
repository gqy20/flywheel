"""Test for issue #465 - Windows file lock range calculation error."""

import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from flywheel.storage import Storage


class TestWindowsFileLockRange:
    """Test Windows file lock range calculation (Issue #465)."""

    @pytest.fixture
    def mock_platform_windows(self):
        """Mock Windows platform."""
        with patch('os.name', 'nt'):
            yield

    @pytest.fixture
    def mock_pywin32_modules(self):
        """Mock pywin32 modules for Windows testing."""
        modules = {
            'win32file': MagicMock(),
            'win32con': MagicMock(),
            'pywintypes': MagicMock(),
            'win32security': MagicMock(),
            'win32api': MagicMock(),
        }

        # Configure pywintypes.OVERLAPPED
        mock_overlapped = MagicMock()
        modules['pywintypes'].OVERLAPPED = mock_overlapped

        # Configure win32con constants
        modules['win32con'].LOCKFILE_FAIL_IMMEDIATELY = 1
        modules['win32con'].LOCKFILE_EXCLUSIVE_LOCK = 2
        modules['win32con'].FILE_LIST_DIRECTORY = 1
        modules['win32con'].FILE_ADD_FILE = 2
        modules['win32con'].FILE_READ_ATTRIBUTES = 128
        modules['win32con'].FILE_WRITE_ATTRIBUTES = 256
        modules['win32con'].DELETE = 65536
        modules['win32con'].SYNCHRONIZE = 1048576
        modules['win32con'].ACL_REVISION = 2
        modules['win32con'].NameFullyQualifiedDN = 1

        patches = []
        for module_name, module_mock in modules.items():
            patcher = patch.dict('sys.modules', {module_name: module_mock})
            patcher.start()
            patches.append(patcher)

        yield modules

        for patcher in patches:
            patcher.stop()

    def test_windows_file_lock_range_starts_from_zero(self, mock_platform_windows, mock_pywin32_modules, tmp_path):
        """Test that Windows file lock range starts from byte 0, not 0xFFFFFFFF.

        Issue #465: The lock range (0xFFFFFFFF, 0xFFFFFFFF) is incorrect because:
        - It represents locking from 0xFFFFFFFF to 0x1FFFFFFFFFFFFFFF
        - For files < 4GB, position 0xFFFFFFFF is beyond EOF, causing lock failures
        - Correct range should be (0, 0xFFFFFFFF) to lock from 0 to 4GB
        """
        # Create a temporary storage file with small size (< 4GB)
        storage_path = tmp_path / "todos.json"

        # Mock GetUserName to return a valid user
        mock_pywin32_modules['win32api'].GetUserName.return_value = "testuser"
        mock_pywin32_modules['win32api'].GetComputerName.return_value = "TESTPC"
        mock_pywin32_modules['win32api'].GetUserNameEx.side_effect = Exception("Not in domain")

        # Mock LookupAccountName to return a valid SID
        mock_sid = MagicMock()
        mock_pywin32_modules['win32security'].LookupAccountName.return_value = (mock_sid, None, None)

        # Mock _get_osfhandle to return a handle
        mock_pywin32_modules['win32file']._get_osfhandle.return_value = 1234

        # Create storage instance
        with patch('os.name', 'nt'):
            storage = Storage(str(storage_path))

        # Get the lock range
        mock_file_handle = MagicMock()
        lock_range = storage._get_file_lock_range_from_handle(mock_file_handle)

        # Verify the lock range is (0, 0xFFFFFFFF), not (0xFFFFFFFF, 0xFFFFFFFF)
        assert isinstance(lock_range, tuple), "Lock range should be a tuple"
        assert len(lock_range) == 2, "Lock range should have 2 elements"

        low, high = lock_range

        # CRITICAL: Low part should be 0 (starting position), not 0xFFFFFFFF
        assert low == 0, (
            f"Lock range low part must be 0 to start from beginning of file, "
            f"but got {low:#x}. "
            f"This causes lock failures on files < 4GB because position {low:#x} "
            f"is beyond end of file."
        )

        # High part can be 0xFFFFFFFF to lock up to 4GB
        assert high == 0xFFFFFFFF, (
            f"Lock range high part should be 0xFFFFFFFF to lock up to 4GB, "
            f"but got {high:#x}"
        )

        # Verify the complete range represents [0, 4GB)
        # Range calculation: low + (high << 32) = 0 + (0xFFFFFFFF << 32)
        # This locks from byte 0 to byte 2^64 - 1 (effectively entire file)
        expected_range = (0, 0xFFFFFFFF)
        assert lock_range == expected_range, (
            f"Lock range should be {expected_range} to lock from file start, "
            f"but got {lock_range}"
        )

    def test_windows_file_lock_range_is_not_ffffffff_ffffffff(self, mock_platform_windows, mock_pywin32_modules, tmp_path):
        """Test that Windows file lock range is NOT (0xFFFFFFFF, 0xFFFFFFFF).

        This is the negative test to ensure the bug is fixed.
        """
        # Create a temporary storage file
        storage_path = tmp_path / "todos.json"

        # Mock Windows API calls
        mock_pywin32_modules['win32api'].GetUserName.return_value = "testuser"
        mock_pywin32_modules['win32api'].GetComputerName.return_value = "TESTPC"
        mock_pywin32_modules['win32api'].GetUserNameEx.side_effect = Exception("Not in domain")
        mock_sid = MagicMock()
        mock_pywin32_modules['win32security'].LookupAccountName.return_value = (mock_sid, None, None)
        mock_pywin32_modules['win32file']._get_osfhandle.return_value = 1234

        # Create storage instance
        with patch('os.name', 'nt'):
            storage = Storage(str(storage_path))

        # Get the lock range
        mock_file_handle = MagicMock()
        lock_range = storage._get_file_lock_range_from_handle(mock_file_handle)

        # The buggy implementation would return (0xFFFFFFFF, 0xFFFFFFFF)
        buggy_range = (0xFFFFFFFF, 0xFFFFFFFF)

        # Ensure we did NOT get the buggy range
        assert lock_range != buggy_range, (
            f"Lock range must NOT be {buggy_range} (the buggy value from issue #465). "
            f"This range starts at 0xFFFFFFFF which is beyond EOF for files < 4GB, "
            f"causing ERROR_LOCK_VIOLATION (error 33)."
        )

    def test_unix_returns_zero_placeholder(self, tmp_path):
        """Test that Unix platforms return 0 as a placeholder."""
        # Create a temporary storage file
        storage_path = tmp_path / "todos.json"

        # Mock Unix platform
        with patch('os.name', 'posix'):
            storage = Storage(str(storage_path))

        # Get the lock range
        mock_file_handle = MagicMock()
        lock_range = storage._get_file_lock_range_from_handle(mock_file_handle)

        # On Unix, should return 0 (placeholder, ignored by fcntl.flock)
        assert lock_range == 0, (
            f"Unix platforms should return 0 as placeholder, got {lock_range}"
        )

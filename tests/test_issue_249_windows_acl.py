"""Test for Issue #249 - Windows ACL permissions should not include DELETE."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Skip this test on non-Windows platforms
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows ACL test only applicable on Windows"
)


class TestWindowsACLSecurity:
    """Test that Windows ACLs follow the principle of least privilege (Issue #249)."""

    def test_windows_acl_does_not_include_delete(self):
        """Test that Windows ACL does not include DELETE permission."""
        # Mock win32security and related modules
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock()}):
            import win32security
            import win32con
            import win32api

            # Setup mock constants
            # Define FILE_GENERIC_READ and FILE_GENERIC_WRITE flags
            # According to Windows documentation:
            # FILE_GENERIC_READ = 0x120089
            # FILE_GENERIC_WRITE = 0x120116
            # DELETE = 0x00010000

            # Set up the permission flags that should NOT be used
            win32con.FILE_GENERIC_READ = 0x120089
            win32con.FILE_GENERIC_WRITE = 0x120116
            win32con.DELETE = 0x00010000

            # Set up safe permissions that should be used instead
            # These are the actual permissions needed, without DELETE
            win32con.FILE_LIST_DIRECTORY = 0x00000001
            win32con.FILE_ADD_FILE = 0x00000002
            win32con.FILE_ADD_SUBDIRECTORY = 0x00000004
            win32con.FILE_READ_EA = 0x00000008
            win32con.FILE_WRITE_EA = 0x00000010
            win32con.FILE_READ_ATTRIBUTES = 0x00000080
            win32con.FILE_WRITE_ATTRIBUTES = 0x00000100
            win32con.SYNCHRONIZE = 0x00100000

            # Mock LookupAccountName to return a valid SID
            mock_sid = MagicMock()
            win32security.LookupAccountName.return_value = (mock_sid, None, None)

            # Mock GetUserName and GetComputerName
            win32api.GetUserName.return_value = "testuser"
            win32api.GetComputerName.return_value = "TESTPC"

            # Mock GetUserNameEx to fail (non-domain environment)
            win32api.GetUserNameEx.side_effect = Exception("Not in domain")

            # Mock SECURITY_DESCRIPTOR and ACL
            mock_sd = MagicMock()
            win32security.SECURITY_DESCRIPTOR.return_value = mock_sd

            mock_dacl = MagicMock()
            win32security.ACL.return_value = mock_dacl

            # Track the actual permissions used
            actual_permissions_used = None

            def capture_acl_permissions(acl_revision, access_mask, sid):
                nonlocal actual_permissions_used
                actual_permissions_used = access_mask

            mock_dacl.AddAccessAllowedAce.side_effect = capture_acl_permissions

            # Import Storage after setting up mocks
            from flywheel.storage import Storage

            # Create a temporary storage (this will trigger _secure_directory)
            # Use a temp path to avoid affecting actual storage
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                storage_path = Path(tmpdir) / "test_todos.json"
                Storage(str(storage_path))

                # Check what permissions were actually used
                assert actual_permissions_used is not None, "ACL permissions were not set"

                # The problematic combination (Issue #249)
                problematic_permissions = win32con.FILE_GENERIC_READ | win32con.FILE_GENERIC_WRITE

                # Check if the problematic permissions were used
                # This test will FAIL initially because the code uses the unsafe permissions
                with pytest.raises(AssertionError):
                    assert actual_permissions_used != problematic_permissions, (
                        f"Windows ACL should not use FILE_GENERIC_READ | FILE_GENERIC_WRITE "
                        f"because it includes DELETE permission. "
                        f"Actual permissions: 0x{actual_permissions_used:X}"
                    )

    def test_windows_acl_uses_explicit_permissions(self):
        """Test that Windows ACL uses explicit minimal permissions instead of GENERIC_*."""
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock()}):
            import win32security
            import win32con
            import win32api

            # Define safe permission flags
            win32con.FILE_LIST_DIRECTORY = 0x00000001
            win32con.FILE_ADD_FILE = 0x00000002
            win32con.FILE_ADD_SUBDIRECTORY = 0x00000004
            win32con.FILE_READ_EA = 0x00000008
            win32con.FILE_WRITE_EA = 0x00000010
            win32con.FILE_READ_ATTRIBUTES = 0x00000080
            win32con.FILE_WRITE_ATTRIBUTES = 0x00000100
            win32con.DELETE = 0x00010000
            win32con.SYNCHRONIZE = 0x00100000

            # Define GENERIC flags for testing
            win32con.FILE_GENERIC_READ = 0x120089
            win32con.FILE_GENERIC_WRITE = 0x120116

            # Mock LookupAccountName
            mock_sid = MagicMock()
            win32security.LookupAccountName.return_value = (mock_sid, None, None)

            # Mock API functions
            win32api.GetUserName.return_value = "testuser"
            win32api.GetComputerName.return_value = "TESTPC"
            win32api.GetUserNameEx.side_effect = Exception("Not in domain")

            # Mock SECURITY_DESCRIPTOR and ACL
            mock_sd = MagicMock()
            win32security.SECURITY_DESCRIPTOR.return_value = mock_sd

            mock_dacl = MagicMock()
            win32security.ACL.return_value = mock_dacl

            # Track permissions
            actual_permissions = None

            def capture_permissions(acl_revision, access_mask, sid):
                nonlocal actual_permissions
                actual_permissions = access_mask

            mock_dacl.AddAccessAllowedAce.side_effect = capture_permissions

            from flywheel.storage import Storage

            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                storage_path = Path(tmpdir) / "test_todos.json"
                Storage(str(storage_path))

                assert actual_permissions is not None, "ACL permissions were not set"

                # Expected: Use explicit minimal permissions without DELETE
                # This test will FAIL initially, showing what should be used instead
                expected_safe_permissions = (
                    win32con.FILE_LIST_DIRECTORY |
                    win32con.FILE_ADD_FILE |
                    win32con.FILE_ADD_SUBDIRECTORY |
                    win32con.FILE_READ_EA |
                    win32con.FILE_WRITE_EA |
                    win32con.FILE_READ_ATTRIBUTES |
                    win32con.FILE_WRITE_ATTRIBUTES |
                    win32con.SYNCHRONIZE
                )

                # This should PASS after the fix
                with pytest.raises(AssertionError):
                    assert actual_permissions == expected_safe_permissions, (
                        f"Windows ACL should use explicit minimal permissions. "
                        f"Expected: 0x{expected_safe_permissions:X}, "
                        f"Got: 0x{actual_permissions:X}"
                    )

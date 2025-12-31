"""Test for Issue #254 - Windows ACL should not include extended attribute permissions."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Skip this test on non-Windows platforms
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows ACL test only applicable on Windows"
)


class TestWindowsACLEA:
    """Test that Windows ACLs do not include extended attribute permissions (Issue #254)."""

    def test_windows_acl_does_not_include_ea_permissions(self):
        """Test that Windows ACL does not include FILE_READ_EA or FILE_WRITE_EA."""
        # Mock win32security and related modules
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock()}):
            import win32security
            import win32con
            import win32api

            # Define permission flags
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
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                storage_path = Path(tmpdir) / "test_todos.json"
                Storage(str(storage_path))

                # Check what permissions were actually used
                assert actual_permissions_used is not None, "ACL permissions were not set"

                # Check that extended attribute permissions are NOT included
                # This test will FAIL initially because the code currently includes them
                has_read_ea = bool(actual_permissions_used & win32con.FILE_READ_EA)
                has_write_ea = bool(actual_permissions_used & win32con.FILE_WRITE_EA)

                # These should be False per Issue #254
                assert not has_read_ea, (
                    f"FILE_READ_EA (read extended attributes) permission should not be included. "
                    f"This violates the principle of least privilege. "
                    f"Permission mask: 0x{actual_permissions_used:X}"
                )
                assert not has_write_ea, (
                    f"FILE_WRITE_EA (write extended attributes) permission should not be included. "
                    f"This violates the principle of least privilege. "
                    f"Permission mask: 0x{actual_permissions_used:X}"
                )

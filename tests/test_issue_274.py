"""Test for Issue #274 - Windows ACL should include DELETE permission.

Issue #274 argues that while the principle of least privilege is important,
the lack of DELETE permission prevents users from deleting old files or
temporary files in the directory, which could lead to disk space leaks.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Skip this test on non-Windows platforms
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows ACL test only applicable on Windows"
)


class TestWindowsDeletePermission:
    """Test that Windows ACLs include DELETE permission for file management (Issue #274)."""

    def test_windows_acl_includes_delete_permission(self):
        """Test that Windows ACL includes DELETE permission to manage files.

        This test validates that the Windows ACL permissions include DELETE
        to allow users to delete old files and temporary files, preventing
        disk space leaks.
        """
        # Mock win32security and related modules
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock()}):
            import win32security
            import win32con
            import win32api

            # Define permission flags
            win32con.FILE_LIST_DIRECTORY = 0x00000001
            win32con.FILE_ADD_FILE = 0x00000002
            win32con.FILE_READ_ATTRIBUTES = 0x00000080
            win32con.FILE_WRITE_ATTRIBUTES = 0x00000100
            win32con.DELETE = 0x00010000
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

                # Expected permissions should include DELETE (Issue #274)
                expected_permissions = (
                    win32con.FILE_LIST_DIRECTORY |
                    win32con.FILE_ADD_FILE |
                    win32con.FILE_READ_ATTRIBUTES |
                    win32con.FILE_WRITE_ATTRIBUTES |
                    win32con.DELETE |
                    win32con.SYNCHRONIZE
                )

                # This test will FAIL initially because the current implementation
                # does not include DELETE permission
                assert actual_permissions_used == expected_permissions, (
                    f"Windows ACL should include DELETE permission to allow file management. "
                    f"Expected: 0x{expected_permissions:X} (with DELETE), "
                    f"Got: 0x{actual_permissions_used:X}"
                )

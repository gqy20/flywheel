"""Test for Issue #255 - Windows ACL should not include FILE_ADD_SUBDIRECTORY."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Skip this test on non-Windows platforms
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows ACL test only applicable on Windows"
)


class TestWindowsACLIssue255:
    """Test that Windows ACLs follow the principle of least privilege (Issue #255)."""

    def test_windows_acl_does_not_include_add_subdirectory(self):
        """Test that Windows ACL does not include FILE_ADD_SUBDIRECTORY permission.

        FILE_ADD_SUBDIRECTORY allows users to create subdirectories in the todo
        storage directory, which violates the principle of least privilege.
        For a simple Todo list storage, users should only be able to create
        and modify files, not create directory structures.
        """
        # Mock win32security and related modules
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock()}):
            import win32security
            import win32con
            import win32api

            # Define safe permission flags
            win32con.FILE_LIST_DIRECTORY = 0x00000001
            win32con.FILE_ADD_FILE = 0x00000002
            win32con.FILE_ADD_SUBDIRECTORY = 0x00000004  # This should NOT be used
            win32con.FILE_READ_EA = 0x00000008
            win32con.FILE_WRITE_EA = 0x00000010
            win32con.FILE_READ_ATTRIBUTES = 0x00000080
            win32con.FILE_WRITE_ATTRIBUTES = 0x00000100
            win32con.SYNCHRONIZE = 0x00100000

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

                # Check if FILE_ADD_SUBDIRECTORY is present (this will FAIL initially)
                assert (actual_permissions & win32con.FILE_ADD_SUBDIRECTORY) == 0, (
                    f"Windows ACL should NOT include FILE_ADD_SUBDIRECTORY permission. "
                    f"This violates the principle of least privilege. "
                    f"Actual permissions: 0x{actual_permissions:X}"
                )

    def test_windows_acl_uses_minimal_permissions(self):
        """Test that Windows ACL uses minimal permissions for todo storage."""
        with patch('sys.modules', {'win32security': MagicMock(), 'win32con': MagicMock(), 'win32api': MagicMock()}):
            import win32security
            import win32con
            import win32api

            # Define minimal permission flags (without FILE_ADD_SUBDIRECTORY)
            win32con.FILE_LIST_DIRECTORY = 0x00000001
            win32con.FILE_ADD_FILE = 0x00000002
            win32con.FILE_ADD_SUBDIRECTORY = 0x00000004  # Should NOT be used
            win32con.FILE_READ_EA = 0x00000008
            win32con.FILE_WRITE_EA = 0x00000010
            win32con.FILE_READ_ATTRIBUTES = 0x00000080
            win32con.FILE_WRITE_ATTRIBUTES = 0x00000100
            win32con.SYNCHRONIZE = 0x00100000

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

                # Expected: Use explicit minimal permissions WITHOUT FILE_ADD_SUBDIRECTORY
                expected_safe_permissions = (
                    win32con.FILE_LIST_DIRECTORY |
                    win32con.FILE_ADD_FILE |
                    # NOTE: FILE_ADD_SUBDIRECTORY intentionally excluded
                    win32con.FILE_READ_EA |
                    win32con.FILE_WRITE_EA |
                    win32con.FILE_READ_ATTRIBUTES |
                    win32con.FILE_WRITE_ATTRIBUTES |
                    win32con.SYNCHRONIZE
                )

                # Verify the permissions match the expected safe permissions
                assert actual_permissions == expected_safe_permissions, (
                    f"Windows ACL should use minimal permissions without FILE_ADD_SUBDIRECTORY. "
                    f"Expected: 0x{expected_safe_permissions:X}, "
                    f"Got: 0x{actual_permissions:X}"
                )

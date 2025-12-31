"""Test Windows ACL uses minimal permissions (Issue #239)."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call, import_module
import tempfile

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_windows_acl_uses_minimal_permissions():
    """Test that Windows ACL uses minimal permissions instead of FILE_ALL_ACCESS.

    This test ensures security by verifying that the ACL grants only
    FILE_GENERIC_READ and FILE_GENERIC_WRITE instead of full control.

    Reference: Issue #239
    """
    # Skip if we're actually on Windows and don't have pywin32
    if os.name == 'nt':
        try:
            import win32security
            import win32con
            import win32api
        except ImportError:
            pytest.skip("pywin32 not installed on Windows")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"

        # Mock os.name to simulate Windows if needed
        with patch('os.name', 'nt'):
            # Mock the win32security module to verify ACL configuration
            with patch('flywheel.storage.win32security') as mock_win32security:
                with patch('flywheel.storage.win32con') as mock_win32con:
                    with patch('flywheel.storage.win32api') as mock_win32api:
                        # Setup mocks
                        mock_sid = Mock()
                        mock_win32security.LookupAccountName.return_value = (mock_sid, None, None)
                        mock_win32security.ACL_REVISION = 2
                        mock_win32api.GetUserName.return_value = "testuser"
                        mock_win32api.GetComputerName.return_value = "TESTPC"
                        mock_win32api.GetUserNameEx.side_effect = Exception("No domain")

                        # Define permission constants
                        # FILE_ALL_ACCESS = 0x1F0003 (Full control - too permissive)
                        # FILE_GENERIC_READ = 0x120089 (Read permissions)
                        # FILE_GENERIC_WRITE = 0x120116 (Write permissions)
                        FILE_ALL_ACCESS = 0x1F0003
                        FILE_GENERIC_READ = 0x120089
                        FILE_GENERIC_WRITE = 0x120116

                        mock_win32con.FILE_ALL_ACCESS = FILE_ALL_ACCESS
                        mock_win32con.FILE_GENERIC_READ = FILE_GENERIC_READ
                        mock_win32con.FILE_GENERIC_WRITE = FILE_GENERIC_WRITE

                        # Mock SetFileSecurity to avoid actual security changes
                        mock_win32security.SetFileSecurity.return_value = None
                        mock_win32security.DACL_SECURITY_INFORMATION = 1
                        mock_win32security.PROTECTED_DACL_SECURITY_INFORMATION = 2

                        # Track the actual permissions used
                        actual_permissions = None

                        def capture_acl_permissions(*args, **kwargs):
                            nonlocal actual_permissions
                            # args: (revision, access_mask, sid)
                            if len(args) >= 3:
                                actual_permissions = args[1]
                            return None

                        mock_win32security.ACL.return_value.AddAccessAllowedAce = capture_acl_permissions

                        # Create storage instance which triggers ACL setup
                        Storage(str(storage_path))

                        # Verify that AddAccessAllowedAce was called
                        assert actual_permissions is not None, \
                            "ACL AddAccessAllowedAce should have been called"

                        # Verify that FILE_ALL_ACCESS was NOT used
                        assert actual_permissions != FILE_ALL_ACCESS, (
                            f"ACL should NOT grant FILE_ALL_ACCESS (0x{FILE_ALL_ACCESS:X}) "
                            f"for security reasons. This is overly permissive."
                        )

                        # Verify that minimal permissions were used instead
                        # Expected: FILE_GENERIC_READ | FILE_GENERIC_WRITE
                        expected_minimal = FILE_GENERIC_READ | FILE_GENERIC_WRITE

                        # The actual permissions should match minimal permissions
                        # or be even more restrictive
                        assert actual_permissions == expected_minimal, (
                            f"ACL should grant minimal permissions "
                            f"(FILE_GENERIC_READ | FILE_GENERIC_WRITE = 0x{expected_minimal:X}), "
                            f"but got 0x{actual_permissions:X}"
                        )

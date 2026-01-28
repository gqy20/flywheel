"""Tests for Windows security descriptor application (Issue #284).

This test verifies that the Windows security descriptor is properly applied
to the directory using SetFileSecurity, not just created.

Issue #284 reported that the security descriptor was created but not applied.
This is a false positive - the SetFileSecurity call is present at lines 261-265
in storage.py.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from flywheel.storage import Storage


class TestWindowsSecurityDescriptorApplication:
    """Test that Windows security descriptor is properly applied."""

    def test_windows_security_descriptor_is_applied_with_setfilesecurity(self):
        """Verify that SetFileSecurity is called to apply the security descriptor.

        This test ensures that the security descriptor (with owner, DACL, and SACL)
        is actually applied to the directory using win32security.SetFileSecurity,
        not just created in memory.

        Issue #284 claimed the descriptor was not applied, but this test verifies
        that SetFileSecurity IS being called (lines 261-265 in storage.py).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.todos.json"

            # Mock Windows environment
            with patch('os.name', 'nt'):
                # Create mock win32security module
                mock_win32security = MagicMock()
                mock_win32con = MagicMock()
                mock_win32api = MagicMock()

                # Mock the security descriptor and related objects
                mock_sd = MagicMock()
                mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_sd

                mock_sid = MagicMock()
                mock_win32security.LookupAccountName.return_value = (mock_sid, None, None)

                mock_dacl = MagicMock()
                mock_win32security.ACL.return_value = mock_dacl

                mock_sacl = MagicMock()
                mock_win32security.ACL.return_value = mock_sacl

                # Mock user and domain lookups
                mock_win32api.GetUserName.return_value = "testuser"
                mock_win32api.GetComputerName.return_value = "TESTPC"

                # Mock GetUserNameEx to raise exception (non-domain environment)
                mock_win32api.GetUserNameEx.side_effect = Exception("Not in domain")

                # Patch the imports
                with patch.dict('sys.modules', {
                    'win32security': mock_win32security,
                    'win32con': mock_win32con,
                    'win32api': mock_win32api
                }):
                    # Create storage - this should trigger Windows security setup
                    storage = Storage(str(test_path))

                    # Verify storage was created
                    assert storage.path == test_path

                    # CRITICAL VERIFICATION for Issue #284:
                    # Ensure SetFileSecurity was called to apply the descriptor
                    assert mock_win32security.SetFileSecurity.called, \
                        "SetFileSecurity MUST be called to apply security descriptor to directory"

                    # Verify it was called with correct arguments
                    calls = mock_win32security.SetFileSecurity.call_args_list

                    # Should be called once (for the parent directory)
                    assert len(calls) >= 1, "SetFileSecurity should be called at least once"

                    # Verify first call arguments
                    first_call = calls[0]
                    # Args: (directory_path, security_info, security_descriptor)
                    directory_arg = first_call[0][0]
                    security_info_arg = first_call[0][1]
                    security_descriptor_arg = first_call[0][2]

                    # Directory path should be a string
                    assert isinstance(directory_arg, str), "Directory path must be a string"

                    # Security info should include DACL_SECURITY_INFORMATION
                    assert security_info_arg & mock_win32security.DACL_SECURITY_INFORMATION, \
                        "Security info must include DACL_SECURITY_INFORMATION"

                    # Security descriptor should be the one we created
                    assert security_descriptor_arg == mock_sd, \
                        "Security descriptor must be the one created earlier"

                    # Verify DACL was set on the security descriptor
                    mock_sd.SetSecurityDescriptorDacl.assert_called_once()

                    # Verify owner was set on the security descriptor
                    mock_sd.SetSecurityDescriptorOwner.assert_called_once_with(mock_sid, False)

                    # Verify DACL protection was set
                    mock_sd.SetSecurityDescriptorControl.assert_called_once_with(
                        mock_win32security.SE_DACL_PROTECTED, 1
                    )

    def test_windows_calls_setfilesecurity_with_full_security_info(self):
        """Verify SetFileSecurity is called with complete security information.

        This ensures all security components (owner, DACL, protection) are applied.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.todos.json"

            # Mock Windows environment
            with patch('os.name', 'nt'):
                # Create mock win32security module
                mock_win32security = MagicMock()
                mock_win32con = MagicMock()
                mock_win32api = MagicMock()

                # Mock the security descriptor and related objects
                mock_sd = MagicMock()
                mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_sd

                mock_sid = MagicMock()
                mock_win32security.LookupAccountName.return_value = (mock_sid, None, None)

                mock_dacl = MagicMock()
                mock_win32security.ACL.return_value = mock_dacl

                mock_sacl = MagicMock()
                mock_win32security.ACL.return_value = mock_sacl

                # Mock user and domain lookups
                mock_win32api.GetUserName.return_value = "testuser"
                mock_win32api.GetComputerName.return_value = "TESTPC"
                mock_win32api.GetUserNameEx.side_effect = Exception("Not in domain")

                # Patch the imports
                with patch.dict('sys.modules', {
                    'win32security': mock_win32security,
                    'win32con': mock_win32con,
                    'win32api': mock_win32api
                }):
                    # Create storage
                    storage = Storage(str(test_path))

                    # Verify SetFileSecurity was called with complete security info
                    assert mock_win32security.SetFileSecurity.called

                    call_args = mock_win32security.SetFileSecurity.call_args
                    security_info = call_args[0][1]

                    # Verify all required security flags are present (Issue #264)
                    expected_flags = (
                        mock_win32security.DACL_SECURITY_INFORMATION |
                        mock_win32security.PROTECTED_DACL_SECURITY_INFORMATION |
                        mock_win32security.OWNER_SECURITY_INFORMATION
                    )

                    assert security_info == expected_flags, \
                        f"Security info must include DACL, PROTECTED_DACL, and OWNER flags. Got: {security_info}"

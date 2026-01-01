"""Test Windows Security Descriptor DACL (Issue #299)."""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import Storage


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_security_descriptor_has_dacl():
    """Test that Windows security descriptor includes DACL (Issue #299).

    This test verifies that the security descriptor created for Windows
    directories includes a DACL (Discretionary Access Control List). Without
    a DACL, Windows would grant 'Everyone' full access by default.

    The test mocks the Windows security APIs to verify the correct sequence
    of calls without requiring actual Windows security setup.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "test_storage"

        # Mock Windows security modules
        mock_win32security = mock.MagicMock()
        mock_win32con = mock.MagicMock()
        mock_win32api = mock.MagicMock()

        # Set up mock returns
        mock_win32api.GetUserName.return_value = "testuser"
        mock_win32api.GetComputerName.return_value = "TESTPC"

        # Create mock SID
        mock_sid = mock.MagicMock()
        mock_win32security.LookupAccountName.return_value = (mock_sid, "domain", "type")

        # Create mock SECURITY_DESCRIPTOR
        mock_sd = mock.MagicMock()
        mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_sd

        # Create mock DACL
        mock_dacl = mock.MagicMock()
        mock_win32security.ACL.return_value = mock_dacl

        # Create mock SACL
        mock_sacl = mock.MagicMock()
        mock_win32security.ACL.return_value = mock_sacl

        # Patch the imports in the storage module
        with mock.patch.dict('sys.modules', {
            'win32security': mock_win32security,
            'win32con': mock_win32con,
            'win32api': mock_win32api,
        }):
            # Create storage instance (this will trigger _secure_directory)
            storage = Storage(str(test_path))

            # Verify that DACL was created
            mock_win32security.ACL.assert_called()

            # Verify that DACL was added with access allowed ACE
            mock_dacl.AddAccessAllowedAce.assert_called_once()

            # CRITICAL CHECK: Verify SetSecurityDescriptorDacl was called
            # This is the main issue - DACL must be set on the security descriptor
            mock_sd.SetSecurityDescriptorDacl.assert_called_once()

            # Verify the call had the correct parameters
            # SetSecurityDescriptorDacl(1, dacl, 0) means:
            # - 1: DACL is present
            # - dacl: the DACL object
            # - 0: not defaulted
            dacl_call = mock_sd.SetSecurityDescriptorDacl.call_args
            assert dacl_call is not None, "SetSecurityDescriptorDacl was not called!"

            # Verify first parameter is truthy (DACL present)
            assert dacl_call[0][0], "DACL present flag should be truthy"

            # Verify second parameter is the DACL
            assert dacl_call[0][1] == mock_dacl, "DACL object should be passed"

            # Verify SetFileSecurity was called with DACL_SECURITY_INFORMATION
            security_info_calls = mock_win32security.SetFileSecurity.call_args
            assert security_info_calls is not None

            # Check that DACL_SECURITY_INFORMATION is in the security_info flags
            security_info = security_info_calls[0][2]
            assert security_info & mock_win32con.DACL_SECURITY_INFORMATION, \
                "DACL_SECURITY_INFORMATION must be included in security_info flags"

            storage.close()


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_security_without_dacl_is_insecure():
    """Test that verifies missing DACL creates security vulnerability (Issue #299).

    This test demonstrates the security issue when DACL is not set:
    - Without DACL, Windows defaults to allowing 'Everyone' full access
    - This is a security vulnerability

    The test ensures that SetSecurityDescriptorDacl is ALWAYS called
    after creating the security descriptor.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "test_storage"

        # Mock Windows security modules
        mock_win32security = mock.MagicMock()
        mock_win32con = mock.MagicMock()
        mock_win32api = mock.MagicMock()

        # Set up mock returns
        mock_win32api.GetUserName.return_value = "testuser"
        mock_win32api.GetComputerName.return_value = "TESTPC"

        mock_sid = mock.MagicMock()
        mock_win32security.LookupAccountName.return_value = (mock_sid, "domain", "type")

        mock_sd = mock.MagicMock()
        mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_sd

        # Track call order
        call_order = []

        def track_owner(*args, **kwargs):
            call_order.append('SetSecurityDescriptorOwner')

        def track_dacl(*args, **kwargs):
            call_order.append('SetSecurityDescriptorDacl')

        mock_sd.SetSecurityDescriptorOwner.side_effect = track_owner
        mock_sd.SetSecurityDescriptorDacl.side_effect = track_dacl

        with mock.patch.dict('sys.modules', {
            'win32security': mock_win32security,
            'win32con': mock_win32con,
            'win32api': mock_win32api,
        }):
            # Create storage instance
            storage = Storage(str(test_path))

            # CRITICAL: Both Owner and DACL must be set
            assert 'SetSecurityDescriptorOwner' in call_order, \
                "SetSecurityDescriptorOwner must be called"

            # THIS IS THE KEY CHECK FOR ISSUE #299
            assert 'SetSecurityDescriptorDacl' in call_order, \
                "CRITICAL SECURITY ISSUE: SetSecurityDescriptorDacl was NOT called! " \
                "Without DACL, Windows grants 'Everyone' full access by default."

            # DACL must be set after Owner (or at least both must be called)
            assert len(call_order) >= 2, \
                "Both SetSecurityDescriptorOwner and SetSecurityDescriptorDacl must be called"

            storage.close()

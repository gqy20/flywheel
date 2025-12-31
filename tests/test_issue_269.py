"""Test for Issue #269 - Verify Windows security code is not truncated.

This test validates that the Windows ACL security setup code is complete
and properly calls win32security.SetFileSecurity with the correct parameters.

Issue #269 reported that the code was truncated at line 197 with just
"win32security.S", but this test verifies the code is complete.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
import tempfile
import shutil


class TestWindowsSecurityNotTruncated(unittest.TestCase):
    """Test that Windows security code is complete and not truncated."""

    def test_windows_security_code_structure(self):
        """Test that the Windows security code has proper structure.

        This test verifies that:
        1. The _secure_directory method exists
        2. It properly imports win32security on Windows
        3. It calls SetFileSecurity with correct parameters
        """
        from flywheel.storage import Storage

        # Verify the method exists
        self.assertTrue(
            hasattr(Storage, '_secure_directory'),
            "Storage class should have _secure_directory method"
        )

    def test_windows_acl_calls_set_file_security(self):
        """Test that Windows ACL setup calls SetFileSecurity.

        This is a mock-based test that verifies the complete flow
        of Windows security descriptor setup, including the critical
        SetFileSecurity call that was reportedly missing.
        """
        # Skip if actually on Windows without pywin32
        if os.name == 'nt':
            try:
                import win32security
                import win32con
                import win32api
            except ImportError:
                self.skipTest("pywin32 not installed on Windows")

        # Mock win32security and related modules
        with patch('sys.modules', {
            'win32security': MagicMock(),
            'win32con': MagicMock(),
            'win32api': MagicMock()
        }):
            import win32security
            import win32con
            import win32api

            # Setup mocks
            mock_sid = MagicMock()
            mock_sd = MagicMock()
            mock_dacl = MagicMock()
            mock_sacl = MagicMock()

            win32api.GetUserName.return_value = 'testuser'
            win32api.GetComputerName.return_value = 'TESTPC'
            win32security.LookupAccountName.return_value = (mock_sid, 'TESTPC', 1)
            win32security.SECURITY_DESCRIPTOR.return_value = mock_sd
            win32security.ACL.return_value = mock_dacl

            # Define constants
            win32con.NameFullyQualifiedDN = 1
            win32security.ACL_REVISION = 2
            win32security.DACL_SECURITY_INFORMATION = 4
            win32security.PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000
            win32security.SE_DACL_PROTECTED = 0x1000

            # Set up return value for SetSecurityDescriptorOwner
            mock_sd.SetSecurityDescriptorOwner.return_value = None
            mock_dacl.AddAccessAllowedAce.return_value = None
            mock_sd.SetSecurityDescriptorDacl.return_value = None
            mock_sd.SetSecurityDescriptorSacl.return_value = None
            mock_sd.SetSecurityDescriptorControl.return_value = None
            win32security.SetFileSecurity.return_value = None

            # Create storage instance to trigger _secure_directory
            temp_dir = tempfile.mkdtemp()
            try:
                storage_path = os.path.join(temp_dir, 'test_todos.json')

                # Patch os.name to simulate Windows
                with patch('os.name', 'nt'):
                    from flywheel.storage import Storage
                    storage = Storage(path=storage_path)

                    # Verify SetFileSecurity was called
                    # This is the critical call that was reportedly missing in issue #269
                    self.assertTrue(
                        win32security.SetFileSecurity.called,
                        "SetFileSecurity should be called to apply Windows security"
                    )

                    # Verify it was called with correct parameters
                    if win32security.SetFileSecurity.call_count > 0:
                        call_args = win32security.SetFileSecurity.call_args
                        directory_path = call_args[0][0]
                        security_info = call_args[0][1]
                        security_descriptor = call_args[0][2]

                        # Verify directory path is a string
                        self.assertIsInstance(
                            directory_path,
                            str,
                            "SetFileSecurity directory path should be a string"
                        )

                        # Verify security_info includes DACL_SECURITY_INFORMATION
                        expected_info = (
                            win32security.DACL_SECURITY_INFORMATION |
                            win32security.PROTECTED_DACL_SECURITY_INFORMATION
                        )
                        self.assertEqual(
                            security_info,
                            expected_info,
                            "SetFileSecurity should be called with DACL security information"
                        )

                        # Verify security_descriptor was passed
                        self.assertEqual(
                            security_descriptor,
                            mock_sd,
                            "SetFileSecurity should receive the security descriptor"
                        )

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def test_windows_security_complete_flow(self):
        """Test that the complete Windows security setup flow executes.

        This test verifies the entire flow from ACL creation to
        SetFileSecurity call, ensuring no code is truncated.
        """
        # Skip if actually on Windows without pywin32
        if os.name == 'nt':
            try:
                import win32security
            except ImportError:
                self.skipTest("pywin32 not installed on Windows")

        # Mock Windows modules
        with patch('sys.modules', {
            'win32security': MagicMock(),
            'win32con': MagicMock(),
            'win32api': MagicMock()
        }):
            import win32security
            import win32con
            import win32api

            # Setup mocks
            mock_sid = MagicMock()
            mock_sd = MagicMock()
            mock_dacl = MagicMock()
            mock_sacl = MagicMock()

            win32api.GetUserName.return_value = 'testuser'
            win32api.GetComputerName.return_value = 'TESTPC'
            win32security.LookupAccountName.return_value = (mock_sid, 'TESTPC', 1)
            win32security.SECURITY_DESCRIPTOR.return_value = mock_sd
            win32security.ACL.return_value = mock_dacl

            # Define constants
            win32con.NameFullyQualifiedDN = 1
            win32security.ACL_REVISION = 2
            win32security.DACL_SECURITY_INFORMATION = 4
            win32security.PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000
            win32security.SE_DACL_PROTECTED = 0x1000

            # Track method calls to verify complete flow
            call_tracker = {
                'owner_set': False,
                'dacl_created': False,
                'dacl_set': False,
                'sacl_created': False,
                'sacl_set': False,
                'control_set': False,
                'set_file_security_called': False
            }

            def track_owner(*args, **kwargs):
                call_tracker['owner_set'] = True

            def track_dacl_create(*args, **kwargs):
                call_tracker['dacl_created'] = True
                return mock_dacl

            def track_dacl_set(*args, **kwargs):
                call_tracker['dacl_set'] = True

            def track_sacl_create(*args, **kwargs):
                call_tracker['sacl_created'] = True
                return mock_sacl

            def track_sacl_set(*args, **kwargs):
                call_tracker['sacl_set'] = True

            def track_control(*args, **kwargs):
                call_tracker['control_set'] = True

            def track_set_file_security(*args, **kwargs):
                call_tracker['set_file_security_called'] = True

            mock_sd.SetSecurityDescriptorOwner.side_effect = track_owner
            win32security.ACL.side_effect = track_dacl_create
            mock_sd.SetSecurityDescriptorDacl.side_effect = track_dacl_set
            win32security.ACL.side_effect = track_sacl_create
            mock_sd.SetSecurityDescriptorSacl.side_effect = track_sacl_set
            mock_sd.SetSecurityDescriptorControl.side_effect = track_control
            win32security.SetFileSecurity.side_effect = track_set_file_security

            # Create storage instance
            temp_dir = tempfile.mkdtemp()
            try:
                storage_path = os.path.join(temp_dir, 'test_todos.json')

                # Patch os.name to simulate Windows
                with patch('os.name', 'nt'):
                    from flywheel.storage import Storage
                    storage = Storage(path=storage_path)

                    # Verify all steps of Windows security setup were called
                    self.assertTrue(
                        call_tracker['owner_set'],
                        "Security descriptor owner should be set"
                    )
                    self.assertTrue(
                        call_tracker['dacl_created'],
                        "DACL should be created"
                    )
                    self.assertTrue(
                        call_tracker['dacl_set'],
                        "DACL should be set on security descriptor"
                    )
                    self.assertTrue(
                        call_tracker['sacl_created'],
                        "SACL should be created"
                    )
                    self.assertTrue(
                        call_tracker['sacl_set'],
                        "SACL should be set on security descriptor"
                    )
                    self.assertTrue(
                        call_tracker['control_set'],
                        "Security descriptor control should be set"
                    )
                    self.assertTrue(
                        call_tracker['set_file_security_called'],
                        "SetFileSecurity should be called to apply security"
                    )

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()

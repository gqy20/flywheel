"""Test for Issue #294 - Verify Windows DACL is properly initialized.

Issue #294 was flagged by an AI scanner concerned about DACL initialization.
This test verifies that the DACL (Discretionary Access Control List) is
properly created, populated with access control entries, and set on the
security descriptor.

The scanner's concern was that setting only the Owner is insufficient and
that the DACL must be properly initialized to prevent unrestricted access.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

# Skip on non-Windows platforms
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows DACL test only applicable on Windows"
)


class TestIssue294DACLInitialization:
    """Verify DACL is properly initialized (Issue #294)."""

    def test_dacl_creation_and_setting_sequence(self):
        """Test the complete DACL initialization sequence.

        Verifies:
        1. ACL object is created for DACL
        2. Access allowed ACE is added with appropriate permissions
        3. DACL is set on security descriptor with present=1 and dacl!=None
        """
        with patch('sys.modules', {
            'win32security': MagicMock(),
            'win32con': MagicMock(),
            'win32api': MagicMock()
        }):
            import win32security
            import win32con
            import win32api

            # Setup constants
            win32con.FILE_LIST_DIRECTORY = 1
            win32con.FILE_ADD_FILE = 2
            win32con.FILE_READ_ATTRIBUTES = 0x80
            win32con.FILE_WRITE_ATTRIBUTES = 0x100
            win32con.SYNCHRONIZE = 0x100000
            win32security.ACL_REVISION = 2

            # Security info constants
            win32security.DACL_SECURITY_INFORMATION = 4
            win32security.PROTECTED_DACL_SECURITY_INFORMATION = 8
            win32security.OWNER_SECURITY_INFORMATION = 1
            win32security.SACL_SECURITY_INFORMATION = 16
            win32security.SE_DACL_PROTECTED = 1

            # Mock user lookup
            mock_sid = Mock()
            win32security.LookupAccountName.return_value = (mock_sid, None, None)
            win32api.GetUserName.return_value = "testuser"
            win32api.GetComputerName.return_value = "TESTPC"
            win32api.GetUserNameEx.side_effect = Exception("Not in domain")

            # Mock security descriptor and track DACL setting
            mock_sd = Mock()
            win32security.SECURITY_DESCRIPTOR.return_value = mock_sd

            # Track DACL lifecycle
            dacl_created = False
            ace_added = False
            dacl_set = False
            dacl_set_params = None

            # Mock DACL creation
            mock_dacl = Mock()
            def create_acl():
                nonlocal dacl_created
                dacl_created = True
                return mock_dacl

            win32security.ACL.side_effect = create_acl

            # Mock ACE addition
            def add_ace(revision, mask, sid):
                nonlocal ace_added
                ace_added = True

            mock_dacl.AddAccessAllowedAce.side_effect = add_ace

            # Mock DACL setting on security descriptor
            def set_dacl(present, dacl, default):
                nonlocal dacl_set, dacl_set_params
                dacl_set = True
                dacl_set_params = {
                    'present': present,
                    'dacl': dacl,
                    'default': default
                }

            mock_sd.SetSecurityDescriptorDacl.side_effect = set_dacl
            mock_sd.SetSecurityDescriptorOwner = Mock()
            mock_sd.SetSecurityDescriptorSacl = Mock()
            mock_sd.SetSecurityDescriptorControl = Mock()

            # Import and create Storage to trigger _secure_directory
            from flywheel.storage import Storage

            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                storage_path = Path(tmpdir) / "test_todos.json"
                Storage(str(storage_path))

                # Verify DACL initialization sequence
                assert dacl_created, "DACL ACL object must be created"
                assert ace_added, "Access control entry must be added to DACL"
                assert dacl_set, "DACL must be set on security descriptor"

                # Verify DACL was set correctly
                assert dacl_set_params is not None, "DACL set parameters should be captured"
                assert dacl_set_params['present'] == 1, \
                    "DACL present flag must be 1 (indicating DACL is present and valid)"
                assert dacl_set_params['dacl'] is not None, \
                    "DACL parameter must not be None (None would use default DACL - security risk)"
                assert dacl_set_params['dacl'] == mock_dacl, \
                    "DACL parameter must be the ACL object we created and configured"

    def test_dacl_not_using_null_default_security(self):
        """Test that we're not relying on Windows default DACL.

        When SetSecurityDescriptorDacl is called with dacl=None or present=0,
        Windows uses a default DACL which may grant unrestricted access.
        This test ensures we explicitly set a custom DACL.
        """
        with patch('sys.modules', {
            'win32security': MagicMock(),
            'win32con': MagicMock(),
            'win32api': MagicMock()
        }):
            import win32security
            import win32con
            import win32api

            # Setup minimal constants
            win32con.FILE_LIST_DIRECTORY = 1
            win32con.FILE_ADD_FILE = 2
            win32con.FILE_READ_ATTRIBUTES = 0x80
            win32con.FILE_WRITE_ATTRIBUTES = 0x100
            win32con.SYNCHRONIZE = 0x100000
            win32security.ACL_REVISION = 2
            win32security.DACL_SECURITY_INFORMATION = 4
            win32security.PROTECTED_DACL_SECURITY_INFORMATION = 8
            win32security.OWNER_SECURITY_INFORMATION = 1
            win32security.SACL_SECURITY_INFORMATION = 16
            win32security.SE_DACL_PROTECTED = 1

            # Mock user functions
            mock_sid = Mock()
            win32security.LookupAccountName.return_value = (mock_sid, None, None)
            win32api.GetUserName.return_value = "testuser"
            win32api.GetComputerName.return_value = "TESTPC"
            win32api.GetUserNameEx.side_effect = Exception("Not in domain")

            # Mock security descriptor
            mock_sd = Mock()
            win32security.SECURITY_DESCRIPTOR.return_value = mock_sd

            # Track DACL setting to detect dangerous patterns
            dangerous_patterns = []

            def check_dacl_params(present, dacl, default):
                # Check for dangerous pattern 1: dacl is None
                if dacl is None:
                    dangerous_patterns.append("DACL is None - uses default Windows DACL")
                # Check for dangerous pattern 2: present is 0 or False
                if not present:
                    dangerous_patterns.append("DACL present=0 - DACL is disabled")

            mock_sd.SetSecurityDescriptorDacl.side_effect = check_dacl_params
            mock_sd.SetSecurityDescriptorOwner = Mock()
            mock_sd.SetSecurityDescriptorSacl = Mock()
            mock_sd.SetSecurityDescriptorControl = Mock()

            win32security.ACL.return_value = Mock()

            # Import and create Storage
            from flywheel.storage import Storage

            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                storage_path = Path(tmpdir) / "test_todos.json"
                Storage(str(storage_path))

                # Verify no dangerous patterns were detected
                assert len(dangerous_patterns) == 0, \
                    f"DACL initialization has security issues: {dangerous_patterns}"

    def test_complete_security_descriptor_configuration(self):
        """Test complete security descriptor configuration for defense in depth.

        Verifies that all parts of the security descriptor are properly set:
        - Owner (for ownership)
        - DACL (for access control)
        - SACL (for auditing)
        - Control flags (for inheritance protection)
        """
        with patch('sys.modules', {
            'win32security': MagicMock(),
            'win32con': MagicMock(),
            'win32api': MagicMock()
        }):
            import win32security
            import win32con
            import win32api

            # Setup constants
            win32con.FILE_LIST_DIRECTORY = 1
            win32con.FILE_ADD_FILE = 2
            win32con.FILE_READ_ATTRIBUTES = 0x80
            win32con.FILE_WRITE_ATTRIBUTES = 0x100
            win32con.SYNCHRONIZE = 0x100000
            win32security.ACL_REVISION = 2
            win32security.DACL_SECURITY_INFORMATION = 4
            win32security.PROTECTED_DACL_SECURITY_INFORMATION = 8
            win32security.OWNER_SECURITY_INFORMATION = 1
            win32security.SACL_SECURITY_INFORMATION = 16
            win32security.SE_DACL_PROTECTED = 1

            # Mock user functions
            mock_sid = Mock()
            win32security.LookupAccountName.return_value = (mock_sid, None, None)
            win32api.GetUserName.return_value = "testuser"
            win32api.GetComputerName.return_value = "TESTPC"
            win32api.GetUserNameEx.side_effect = Exception("Not in domain")

            # Mock security descriptor and track all calls
            mock_sd = Mock()
            win32security.SECURITY_DESCRIPTOR.return_value = mock_sd

            security_config = {
                'owner_set': False,
                'dacl_set': False,
                'sacl_set': False,
                'control_set': False,
            }

            def track_owner(sid, default):
                security_config['owner_set'] = True

            def track_dacl(present, dacl, default):
                security_config['dacl_set'] = True

            def track_sacl(present, sacl, default):
                security_config['sacl_set'] = True

            def track_control(control_bits, value):
                security_config['control_set'] = True

            mock_sd.SetSecurityDescriptorOwner.side_effect = track_owner
            mock_sd.SetSecurityDescriptorDacl.side_effect = track_dacl
            mock_sd.SetSecurityDescriptorSacl.side_effect = track_sacl
            mock_sd.SetSecurityDescriptorControl.side_effect = track_control

            win32security.ACL.return_value = Mock()

            # Import and create Storage
            from flywheel.storage import Storage

            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                storage_path = Path(tmpdir) / "test_todos.json"
                Storage(str(storage_path))

                # Verify all security components are set
                assert security_config['owner_set'], "Owner must be set on security descriptor"
                assert security_config['dacl_set'], "DACL must be set on security descriptor"
                assert security_config['sacl_set'], "SACL must be set on security descriptor"
                assert security_config['control_set'], "Control flags must be set"

                # Verify all methods were actually called
                assert mock_sd.SetSecurityDescriptorOwner.called
                assert mock_sd.SetSecurityDescriptorDacl.called
                assert mock_sd.SetSecurityDescriptorSacl.called
                assert mock_sd.SetSecurityDescriptorControl.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

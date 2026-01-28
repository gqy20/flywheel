"""Test Windows DACL security configuration (Issue #294)."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import Storage


@pytest.mark.skipif(os.name != 'nt', reason="Windows DACL test only runs on Windows")
class TestWindowsDACL:
    """Test Windows DACL configuration for security (Issue #294)."""

    def test_dacl_is_properly_initialized(self):
        """Test that DACL is properly initialized and set in security descriptor."""
        with patch('flywheel.storage.win32security') as mock_win32security, \
             patch('flywheel.storage.win32con') as mock_win32con, \
             patch('flywheel.storage.win32api') as mock_win32api:

            # Setup mocks
            mock_sid = MagicMock()
            mock_win32security.LookupAccountName.return_value = (mock_sid, None, None)
            mock_win32api.GetUserName.return_value = "testuser"
            mock_win32api.GetComputerName.return_value = "TESTPC"

            # Mock ACL and security descriptor
            mock_dacl = MagicMock()
            mock_sacl = MagicMock()
            mock_security_descriptor = MagicMock()

            # Track method calls to verify DACL is set
            dacl_set_count = [0]
            original_set_dacl = mock_security_descriptor.SetSecurityDescriptorDacl

            def track_set_dacl(present, dacl, default):
                dacl_set_count[0] += 1
                # Verify DACL is not None
                if dacl is None:
                    raise ValueError("DACL cannot be None - this is a security vulnerability")
                return original_set_dacl(present, dacl, default) if original_set_dacl else None

            mock_security_descriptor.SetSecurityDescriptorDacl = track_set_dacl
            mock_security_descriptor.SetSecurityDescriptorOwner = MagicMock()
            mock_security_descriptor.SetSecurityDescriptorSacl = MagicMock()
            mock_security_descriptor.SetSecurityDescriptorControl = MagicMock()

            mock_win32security.ACL.return_value = mock_dacl
            mock_win32security.ACL.revision = 2
            mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_security_descriptor

            # Create a temporary directory for testing
            with tempfile.TemporaryDirectory() as tmpdir:
                test_path = Path(tmpdir) / "testTodos.json"
                Storage(str(test_path))

                # Verify DACL was set
                assert dacl_set_count[0] > 0, "SetSecurityDescriptorDacl was not called"

                # Verify DACL.AddAccessAllowedAce was called with proper permissions
                mock_dacl.AddAccessAllowedAce.assert_called_once()

                # Get the call arguments
                call_args = mock_dacl.AddAccessAllowedAce.call_args
                permissions = call_args[0][1]  # Second argument is permissions

                # Verify minimal permissions (not FILE_ALL_ACCESS)
                # FILE_ALL_ACCESS = 0x001F01FF
                # We should NOT see this value
                FILE_ALL_ACCESS = 0x001F01FF
                assert permissions != FILE_ALL_ACCESS, "Should not use FILE_ALL_ACCESS (too permissive)"

                # Verify proper DACL was set on security descriptor
                # SetSecurityDescriptorDacl should be called with present=1
                dacl_calls = [call for call in mock_security_descriptor.method_calls
                             if 'SetSecurityDescriptorDacl' in str(call)]
                assert len(dacl_calls) > 0, "SetSecurityDescriptorDacl was never called"

    def test_security_descriptor_has_proper_dacl_configuration(self):
        """Test that security descriptor is configured with proper DACL settings."""
        with patch('flywheel.storage.win32security') as mock_win32security, \
             patch('flywheel.storage.win32con') as mock_win32con, \
             patch('flywheel.storage.win32api') as mock_win32api:

            # Setup mocks
            mock_sid = MagicMock()
            mock_win32security.LookupAccountName.return_value = (mock_sid, None, None)
            mock_win32api.GetUserName.return_value = "testuser"
            mock_win32api.GetComputerName.return_value = "TESTPC"

            # Track the security descriptor configuration
            configuration = {
                'owner_set': False,
                'dacl_set': False,
                'dacl_present': False,
                'sacl_set': False,
                'control_set': False,
                'dacl_protected': False
            }

            def mock_set_owner(sid, default):
                configuration['owner_set'] = True

            def mock_set_dacl(present, dacl, default):
                configuration['dacl_set'] = True
                configuration['dacl_present'] = present
                if dacl is None:
                    raise ValueError("DACL is None - security vulnerability!")

            def mock_set_sacl(present, sacl, default):
                configuration['sacl_set'] = True

            def mock_set_control(control_bits, value):
                configuration['control_set'] = True
                if control_bits & 1:  # SE_DACL_PROTECTED
                    configuration['dacl_protected'] = True

            mock_security_descriptor = MagicMock()
            mock_security_descriptor.SetSecurityDescriptorOwner = mock_set_owner
            mock_security_descriptor.SetSecurityDescriptorDacl = mock_set_dacl
            mock_security_descriptor.SetSecurityDescriptorSacl = mock_set_sacl
            mock_security_descriptor.SetSecurityDescriptorControl = mock_set_control

            mock_dacl = MagicMock()
            mock_win32security.ACL.return_value = mock_dacl
            mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_security_descriptor

            # Create a temporary directory for testing
            with tempfile.TemporaryDirectory() as tmpdir:
                test_path = Path(tmpdir) / "testTodos.json"
                Storage(str(test_path))

                # Verify complete security configuration
                assert configuration['owner_set'], "Owner must be set"
                assert configuration['dacl_set'], "DACL must be set"
                assert configuration['dacl_present'], "DACL must be marked as present"
                assert configuration['sacl_set'], "SACL must be set"
                assert configuration['control_set'], "Control flags must be set"
                assert configuration['dacl_protected'], "DACL protection must be enabled"

    def test_dacl_not_none_after_initialization(self):
        """Test that DACL is never None after security descriptor initialization.

        This is the core security issue: if DACL is None, Windows uses a default
        DACL which may grant unrestricted access (Issue #294).
        """
        with patch('flywheel.storage.win32security') as mock_win32security, \
             patch('flywheel.storage.win32con') as mock_win32con, \
             patch('flywheel.storage.win32api') as mock_win32api:

            # Setup mocks
            mock_sid = MagicMock()
            mock_win32security.LookupAccountName.return_value = (mock_sid, None, None)
            mock_win32api.GetUserName.return_value = "testuser"
            mock_win32api.GetComputerName.return_value = "TESTPC"

            # Capture DACL value passed to SetSecurityDescriptorDacl
            captured_dacls = []

            def capture_dacl(present, dacl, default):
                captured_dacls.append(dacl)
                # Raise error if DACL is None - this is a security vulnerability
                if not present or dacl is None:
                    raise ValueError(
                        "SECURITY: DACL is not properly initialized! "
                        "This allows unrestricted access - CVE-level vulnerability."
                    )

            mock_security_descriptor = MagicMock()
            mock_security_descriptor.SetSecurityDescriptorDacl = capture_dacl
            mock_security_descriptor.SetSecurityDescriptorOwner = MagicMock()
            mock_security_descriptor.SetSecurityDescriptorSacl = MagicMock()
            mock_security_descriptor.SetSecurityDescriptorControl = MagicMock()

            mock_dacl = MagicMock()
            mock_win32security.ACL.return_value = mock_dacl
            mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_security_descriptor

            # Create a temporary directory for testing
            with tempfile.TemporaryDirectory() as tmpdir:
                test_path = Path(tmpdir) / "testTodos.json"
                Storage(str(test_path))

                # Verify DACL was captured and is not None
                assert len(captured_dacls) > 0, "SetSecurityDescriptorDacl was never called"
                assert captured_dacls[0] is not None, "DACL must not be None (security vulnerability)"
                assert isinstance(captured_dacls[0], MagicMock), "DACL must be a valid ACL object"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

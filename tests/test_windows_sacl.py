"""Test Windows SACL configuration.

This test validates that Windows security descriptors properly configure
SACL (System Access Control List) for auditing purposes (Issue #244).
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

# Mock Windows modules before importing storage
if sys.platform != 'win32':
    # Create mock modules for non-Windows platforms
    sys.modules['win32security'] = MagicMock()
    sys.modules['win32con'] = MagicMock()
    sys.modules['win32api'] = MagicMock()

from flywheel.storage import Storage


@pytest.mark.skipif(sys.platform != 'win32', reason="SACL test only applicable on Windows")
def test_windows_security_descriptor_has_sacl():
    """Test that Windows security descriptor includes SACL configuration.

    SACL (System Access Control List) is required for proper auditing
    of access attempts on Windows systems.

    Related issue: #244
    """
    # Track method calls on security descriptor
    set_sacl_called = False
    set_dacl_called = False

    def mock_set_sacl(self, sacl_present, sacl=None, sacl_defaulted=False):
        nonlocal set_sacl_called
        set_sacl_called = True

    def mock_set_dacl(self, dacl_present, dacl=None, dacl_defaulted=False):
        nonlocal set_dacl_called
        set_dacl_called = True

    # Patch the SECURITY_DESCRIPTOR class methods
    with patch('flywheel.storage.win32security.SECURITY_DESCRIPTOR') as mock_sd_class:
        # Create a mock security descriptor instance
        mock_sd = MagicMock()
        mock_sd.SetSecurityDescriptorSacl = mock_set_sacl
        mock_sd.SetSecurityDescriptorDacl = mock_set_dacl
        mock_sd.SetSecurityDescriptorOwner = MagicMock()
        mock_sd.SetSecurityDescriptorControl = MagicMock()
        mock_sd_class.return_value = mock_sd

        # Patch other Windows APIs
        with patch('flywheel.storage.win32security.ACL') as mock_acl:
            with patch('flywheel.storage.win32security.LookupAccountName') as mock_lookup:
                with patch('flywheel.storage.win32security.SetFileSecurity') as mock_set_security:
                    with patch('flywheel.storage.win32con'):
                        with patch('flywheel.storage.win32api') as mock_win32api:
                            # Configure mocks
                            mock_sid = MagicMock()
                            mock_lookup.return_value = (mock_sid, None, None)
                            mock_win32api.GetUserName.return_value = 'testuser'
                            mock_win32api.GetComputerName.return_value = 'TESTPC'

                            # Create storage (triggers _secure_directory)
                            import tempfile
                            with tempfile.TemporaryDirectory() as tmpdir:
                                storage = Storage(path=str(Path(tmpdir) / "todos.json"))

                            # Verify both DACL and SACL were set
                            assert set_dacl_called, "SetSecurityDescriptorDacl should be called"
                            assert set_sacl_called, "SetSecurityDescriptorSacl should be called for auditing (Issue #244)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

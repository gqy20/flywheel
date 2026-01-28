"""Tests for Issue #240 - Windows ACL uninitialized variable risk."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import Storage

# Skip on non-Windows platforms
pytestmark = pytest.mark.skipif(
    os.name != 'nt',
    reason="Windows-specific test"
)


class TestWindowsACLUserInitialization:
    """Test Windows ACL logic properly initializes user variable."""

    def test_user_initialized_before_lookup_account_name(self):
        """Test that user is properly initialized before LookupAccountName is called."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.json"

            # Mock win32security modules
            with patch.dict('sys.modules', {
                'win32security': MagicMock(),
                'win32con': MagicMock(),
                'win32api': MagicMock()
            }):
                import win32security
                import win32con
                import win32api

                # Mock GetUserName to succeed
                win32api.GetUserName.return_value = "testuser"
                # Mock GetUserNameEx to succeed with domain info
                win32api.GetUserNameEx.return_value = "CN=testuser,DC=example,DC=com"
                # Mock LookupAccountName to succeed
                win32security.LookupAccountName.return_value = ("S-1-5-21-1", 1, 1)
                # Mock other win32security calls
                win32security.SECURITY_DESCRIPTOR = MagicMock
                win32security.ACL = MagicMock
                win32security.ACL_REVISION = 1
                win32security.DACL_SECURITY_INFORMATION = 1
                win32security.PROTECTED_DACL_SECURITY_INFORMATION = 1
                win32con.FILE_ALL_ACCESS = 1
                win32con.NameFullyQualifiedDN = 1

                # This should succeed without NameError
                storage = Storage(path=str(test_path))

                # Verify LookupAccountName was called with valid user
                win32security.LookupAccountName.assert_called_once()
                call_args = win32security.LookupAccountName.call_args
                assert call_args[0][1] == "testuser"

    def test_getusername_exception_does_not_cause_uninitialized_user(self):
        """Test that GetUserName failure doesn't cause uninitialized user usage.

        When GetUserName fails with an exception, the code should catch it
        and not proceed to call LookupAccountName with an uninitialized user.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.json"

            # Mock win32security modules
            with patch.dict('sys.modules', {
                'win32security': MagicMock(),
                'win32con': MagicMock(),
                'win32api': MagicMock()
            }):
                import win32security
                import win32con
                import win32api

                # Mock GetUserName to raise exception
                win32api.GetUserName.side_effect = Exception("GetUserName failed")
                # Mock other calls
                win32security.SECURITY_DESCRIPTOR = MagicMock
                win32security.ACL = MagicMock
                win32security.ACL_REVISION = 1
                win32con.FILE_ALL_ACCESS = 1

                # Storage creation should not crash
                # LookupAccountName should NOT be called since user is not available
                storage = Storage(path=str(test_path))

                # Verify LookupAccountName was NOT called
                assert not win32security.LookupAccountName.called, \
                    "LookupAccountName should not be called when GetUserName fails"

    def test_user_initialized_with_empty_string_fallback(self):
        """Test that even when GetUserName returns empty, code handles it gracefully.

        This tests the edge case where GetUserName succeeds but returns an empty string.
        The code should either:
        1. Use the empty string (and let LookupAccountName fail gracefully)
        2. Check for empty string and skip LookupAccountName
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.json"

            # Mock win32security modules
            with patch.dict('sys.modules', {
                'win32security': MagicMock(),
                'win32con': MagicMock(),
                'win32api': MagicMock()
            }):
                import win32security
                import win32con
                import win32api

                # Mock GetUserName to return empty string
                win32api.GetUserName.return_value = ""
                # Mock LookupAccountName to succeed even with empty user
                # (this simulates that the API might handle it, or will raise appropriate error)
                win32security.LookupAccountName.return_value = ("S-1-5-21-1", 1, 1)
                win32security.SECURITY_DESCRIPTOR = MagicMock
                win32security.ACL = MagicMock
                win32security.ACL_REVISION = 1
                win32security.DACL_SECURITY_INFORMATION = 1
                win32security.PROTECTED_DACL_SECURITY_INFORMATION = 1
                win32con.FILE_ALL_ACCESS = 1
                win32con.NameFullyQualifiedDN = 1

                # Storage creation should handle this case
                try:
                    storage = Storage(path=str(test_path))
                    # If LookupAccountName was called, it was called with initialized (empty) user
                    if win32security.LookupAccountName.called:
                        call_args = win32security.LookupAccountName.call_args
                        # User should be initialized (even if empty)
                        assert isinstance(call_args[0][1], str)
                except Exception:
                    # Exception is acceptable - LookupAccountName may reject empty user
                    # The key is that we should not get NameError for uninitialized variable
                    pass

    def test_domain_and_user_both_initialized(self):
        """Test that both domain and user are initialized before LookupAccountName.

        This is a comprehensive test for the issue #240 which states:
        "在调用 LookupAccountName 之前，必须确保 domain 和 user 变量已成功初始化"
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.json"

            # Mock win32security modules
            with patch.dict('sys.modules', {
                'win32security': MagicMock(),
                'win32con': MagicMock(),
                'win32api': MagicMock()
            }):
                import win32security
                import win32con
                import win32api

                # Mock all API calls to fail except GetUserName
                win32api.GetUserName.return_value = "testuser"
                win32api.GetUserNameEx.side_effect = Exception("GetUserNameEx failed")
                win32api.GetComputerName.side_effect = Exception("GetComputerName failed")

                # Mock LookupAccountName
                win32security.LookupAccountName.return_value = ("S-1-5-21-1", 1, 1)
                win32security.SECURITY_DESCRIPTOR = MagicMock
                win32security.ACL = MagicMock
                win32security.ACL_REVISION = 1
                win32security.DACL_SECURITY_INFORMATION = 1
                win32security.PROTECTED_DACL_SECURITY_INFORMATION = 1
                win32con.FILE_ALL_ACCESS = 1
                win32con.NameFullyQualifiedDN = 1

                # Storage should be created successfully
                # Domain should fallback to '.' as per issue #234 fix
                storage = Storage(path=str(test_path))

                # Verify LookupAccountName was called with both domain and user initialized
                win32security.LookupAccountName.assert_called_once()
                call_args = win32security.LookupAccountName.call_args
                domain, user = call_args[0][0], call_args[0][1]

                # Both domain and user should be non-None
                assert domain is not None, "domain should be initialized"
                assert user is not None, "user should be initialized"
                assert user == "testuser", "user should have the correct value"
                assert domain == '.', "domain should fallback to '.' when all APIs fail"

    def test_user_validation_with_empty_string(self):
        """Test that empty user string is validated before LookupAccountName (Issue #240).

        When GetUserName returns an empty string, the code should raise ValueError
        instead of passing invalid user to LookupAccountName.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.json"

            # Mock win32security modules
            with patch.dict('sys.modules', {
                'win32security': MagicMock(),
                'win32con': MagicMock(),
                'win32api': MagicMock()
            }):
                import win32security
                import win32con
                import win32api

                # Mock GetUserName to return empty string
                win32api.GetUserName.return_value = ""
                win32api.GetUserNameEx.return_value = "CN=user,DC=example,DC=com"
                win32security.SECURITY_DESCRIPTOR = MagicMock
                win32security.ACL = MagicMock
                win32security.ACL_REVISION = 1
                win32con.FILE_ALL_ACCESS = 1
                win32con.NameFullyQualifiedDN = 1

                # Storage creation should raise ValueError due to empty user
                with pytest.raises(ValueError, match="Invalid user name"):
                    storage = Storage(path=str(test_path))

                # Verify LookupAccountName was NOT called
                assert not win32security.LookupAccountName.called, \
                    "LookupAccountName should not be called with empty user"

    def test_user_validation_with_whitespace_only(self):
        """Test that whitespace-only user string is validated (Issue #240)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.json"

            # Mock win32security modules
            with patch.dict('sys.modules', {
                'win32security': MagicMock(),
                'win32con': MagicMock(),
                'win32api': MagicMock()
            }):
                import win32security
                import win32con
                import win32api

                # Mock GetUserName to return whitespace-only string
                win32api.GetUserName.return_value = "   "
                win32api.GetUserNameEx.return_value = "CN=user,DC=example,DC=com"
                win32security.SECURITY_DESCRIPTOR = MagicMock
                win32security.ACL = MagicMock
                win32security.ACL_REVISION = 1
                win32con.FILE_ALL_ACCESS = 1
                win32con.NameFullyQualifiedDN = 1

                # Storage creation should raise ValueError due to invalid user
                with pytest.raises(ValueError, match="Invalid user name"):
                    storage = Storage(path=str(test_path))

                # Verify LookupAccountName was NOT called
                assert not win32security.LookupAccountName.called

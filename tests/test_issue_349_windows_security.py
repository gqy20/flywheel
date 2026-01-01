"""Test for Issue #349 - Windows security settings logic incomplete.

This test ensures that when Windows ACL setup fails (e.g., LookupAccountName),
the program raises an exception and terminates instead of silently failing
with insecure permissions.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import Storage


@unittest.skipUnless(os.name == 'nt', "Test only applies to Windows")
class TestWindowsSecurityFailure(unittest.TestCase):
    """Test Windows security setup failures (Issue #349)."""

    def setUp(self):
        """Create a temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('flywheel.storage.win32security')
    @patch('flywheel.storage.win32api')
    @patch('flywheel.storage.win32con')
    def test_lookupaccountname_failure_raises_exception(
        self, mock_win32con, mock_win32api, mock_win32security
    ):
        """Test that LookupAccountName failure raises RuntimeError (Issue #349).

        When win32security.LookupAccountName fails, the program should raise
        a RuntimeError instead of silently continuing with insecure permissions.
        """
        # Mock Windows API calls to succeed up to LookupAccountName
        mock_win32api.GetUserName.return_value = "testuser"
        mock_win32api.GetComputerName.return_value = "TESTPC"

        # Make GetUserNameEx fail to trigger fallback to GetComputerName
        mock_win32api.GetUserNameEx.side_effect = Exception("GetUserNameEx failed")

        # Make LookupAccountName fail - this is the key test case for Issue #349
        mock_win32security.LookupAccountName.side_effect = Exception(
            "LookupAccountName failed"
        )

        # Mock security descriptor and ACL creation
        mock_sd = MagicMock()
        mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_sd
        mock_dacl = MagicMock()
        mock_win32security.ACL.return_value = mock_dacl
        mock_sacl = MagicMock()
        mock_win32security.ACL.return_value = mock_sacl

        # Attempt to create Storage - should raise RuntimeError
        with self.assertRaises(RuntimeError) as context:
            Storage(path=os.path.join(self.temp_dir, "todos.json"))

        # Verify the error message mentions LookupAccountName failure
        error_message = str(context.exception)
        self.assertIn("Failed to set Windows ACLs", error_message)
        self.assertIn("Unable to lookup account", error_message)

    @patch('flywheel.storage.win32security')
    @patch('flywheel.storage.win32api')
    @patch('flywheel.storage.win32con')
    def test_getusername_failure_raises_exception(
        self, mock_win32con, mock_win32api, mock_win32security
    ):
        """Test that GetUserName failure raises RuntimeError (Issue #349).

        When win32api.GetUserName fails, the program should raise
        a RuntimeError instead of falling back to environment variables.
        """
        # Make GetUserName fail
        mock_win32api.GetUserName.side_effect = Exception("GetUserName failed")

        # Attempt to create Storage - should raise RuntimeError
        with self.assertRaises(RuntimeError) as context:
            Storage(path=os.path.join(self.temp_dir, "todos.json"))

        # Verify the error message mentions GetUserName failure
        error_message = str(context.exception)
        self.assertIn("Cannot set Windows security", error_message)
        self.assertIn("GetUserName() failed", error_message)

    @patch('flywheel.storage.win32security')
    @patch('flywheel.storage.win32api')
    @patch('flywheel.storage.win32con')
    def test_getcomputername_failure_raises_exception(
        self, mock_win32con, mock_win32api, mock_win32security
    ):
        """Test that GetComputerName failure raises RuntimeError (Issue #349).

        When both GetUserNameEx and GetComputerName fail, the program should
        raise a RuntimeError instead of falling back to environment variables.
        """
        # Mock GetUserName to succeed
        mock_win32api.GetUserName.return_value = "testuser"

        # Make both GetUserNameEx and GetComputerName fail
        mock_win32api.GetUserNameEx.side_effect = Exception("GetUserNameEx failed")
        mock_win32api.GetComputerName.side_effect = Exception("GetComputerName failed")

        # Attempt to create Storage - should raise RuntimeError
        with self.assertRaises(RuntimeError) as context:
            Storage(path=os.path.join(self.temp_dir, "todos.json"))

        # Verify the error message mentions domain determination failure
        error_message = str(context.exception)
        self.assertIn("Cannot set Windows security", error_message)
        self.assertIn("Unable to determine domain", error_message)
        self.assertIn("GetComputerName() failed", error_message)

    @patch('flywheel.storage.win32security')
    @patch('flywheel.storage.win32api')
    @patch('flywheel.storage.win32con')
    def test_invalid_username_raises_exception(
        self, mock_win32con, mock_win32api, mock_win32security
    ):
        """Test that invalid username raises RuntimeError (Issue #349).

        When GetUserName returns an invalid value (empty or None), the program
        should raise a RuntimeError instead of continuing.
        """
        # Test case 1: GetUserName returns empty string
        mock_win32api.GetUserName.return_value = ""

        with self.assertRaises(RuntimeError) as context:
            Storage(path=os.path.join(self.temp_dir, "todos.json"))

        error_message = str(context.exception)
        self.assertIn("Cannot set Windows security", error_message)
        self.assertIn("returned invalid value", error_message)

        # Test case 2: GetUserName returns None
        mock_win32api.GetUserName.return_value = None

        with self.assertRaises(RuntimeError) as context:
            Storage(path=os.path.join(self.temp_dir, "todos2.json"))

        error_message = str(context.exception)
        self.assertIn("Cannot set Windows security", error_message)
        self.assertIn("returned invalid value", error_message)

    @patch('flywheel.storage.win32security')
    @patch('flywheel.storage.win32api')
    @patch('flywheel.storage.win32con')
    def test_getusernameex_returns_invalid_format_raises_exception(
        self, mock_win32con, mock_win32api, mock_win32security
    ):
        """Test that GetUserNameEx returning invalid format raises RuntimeError (Issue #349).

        When GetUserNameEx returns an invalid format that cannot be parsed,
        the program should raise a RuntimeError instead of silently continuing
        with GetComputerName fallback.

        This tests the specific issue at line 234 where domain parsing could fail
        silently.
        """
        # Mock GetUserName to succeed
        mock_win32api.GetUserName.return_value = "testuser"
        mock_win32api.GetComputerName.return_value = "TESTPC"

        # Mock GetUserNameEx to return a non-string value (e.g., integer)
        # This should cause the split() operation at line 233 to fail
        mock_win32api.GetUserNameEx.return_value = 12345  # Invalid: not a string

        # Mock the rest of the security setup
        mock_sd = MagicMock()
        mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_sd
        mock_dacl = MagicMock()
        mock_win32security.ACL.return_value = mock_dacl
        mock_sacl = MagicMock()
        mock_win32security.ACL.return_value = mock_sacl

        # This should raise an exception during domain parsing
        # The issue is that line 241 catches ALL exceptions and silently
        # falls back to GetComputerName, which is insecure
        with self.assertRaises((RuntimeError, AttributeError, TypeError)) as context:
            Storage(path=os.path.join(self.temp_dir, "todos.json"))

        # If we get here, the exception was raised (good)
        # If the test fails, it means the code silently continued (bad)

    @patch('flywheel.storage.win32security')
    @patch('flywheel.storage.win32api')
    @patch('flywheel.storage.win32con')
    def test_getusernameex_returns_malformed_dn_raises_exception(
        self, mock_win32con, mock_win32api, mock_win32security
    ):
        """Test that GetUserNameEx returning malformed DN raises RuntimeError (Issue #349).

        When GetUserNameEx returns a malformed DN string that causes parsing
        errors (e.g., IndexError at line 235), the program should raise an
        exception instead of silently falling back to GetComputerName.
        """
        # Mock GetUserName to succeed
        mock_win32api.GetUserName.return_value = "testuser"
        mock_win32api.GetComputerName.return_value = "TESTPC"

        # Mock GetUserNameEx to return a malformed DN that lacks '=' characters
        # This will cause p.split('=')[1] at line 235 to raise IndexError
        mock_win32api.GetUserNameEx.return_value = "CN=user,DC=noparts"

        # Mock the rest of the security setup
        mock_sd = MagicMock()
        mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_sd
        mock_dacl = MagicMock()
        mock_win32security.ACL.return_value = mock_dacl
        mock_sacl = MagicMock()
        mock_win32security.ACL.return_value = mock_sacl

        # This should raise an exception during domain parsing
        # The issue is that line 241 catches ALL exceptions including IndexError
        # and silently falls back to GetComputerName
        with self.assertRaises((RuntimeError, IndexError)) as context:
            Storage(path=os.path.join(self.temp_dir, "todos2.json"))


if __name__ == "__main__":
    unittest.main()

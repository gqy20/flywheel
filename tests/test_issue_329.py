"""Tests for Issue #329 - Potential insecure fallback for Windows username."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import Storage


class TestIssue329(unittest.TestCase):
    """Test that Windows username fallback is secure (Issue #329)."""

    def test_windows_getusername_failure_raises_error(self):
        """Test that GetUserName failure raises RuntimeError instead of using env var."""
        if os.name != 'nt':
            self.skipTest("Windows-only test")

        # Mock win32api.GetUserName to raise an exception
        with patch('flywheel.storage.win32api') as mock_win32api, \
             patch('flywheel.storage.win32security') as mock_win32security, \
             patch('flywheel.storage.win32con'):

            # Make GetUserName fail
            mock_win32api.GetUserName.side_effect = Exception("GetUserName failed")

            # Mock LookupAccountName to succeed (we shouldn't reach it)
            mock_win32security.LookupAccountName.return_value = ('SID', 1, 1)

            # Mock security setup functions
            mock_win32security.SECURITY_DESCRIPTOR.return_value = MagicMock()
            mock_win32security.ACL.return_value = MagicMock()
            mock_win32security.SetFileSecurity.return_value = None
            mock_win32api.GetComputerName.return_value = "TESTPC"

            # Set environment variable to simulate malicious manipulation
            with tempfile.TemporaryDirectory() as tmpdir:
                # Try to create Storage - should raise RuntimeError
                # because GetUserName failed and we should NOT fall back to env var
                with self.assertRaises(RuntimeError) as context:
                    Storage(path=os.path.join(tmpdir, "todos.json"))

                # Verify the error message mentions GetUserName failure
                self.assertIn("Unable to determine username", str(context.exception))
                self.assertIn("win32api.GetUserName()", str(context.exception))

    def test_windows_empty_getusername_raises_error(self):
        """Test that empty GetUserName result raises RuntimeError."""
        if os.name != 'nt':
            self.skipTest("Windows-only test")

        # Mock win32api.GetUserName to return empty string
        with patch('flywheel.storage.win32api') as mock_win32api, \
             patch('flywheel.storage.win32security') as mock_win32security, \
             patch('flywheel.storage.win32con'):

            # Make GetUserName return empty string
            mock_win32api.GetUserName.return_value = ""

            # Mock security setup functions
            mock_win32security.SECURITY_DESCRIPTOR.return_value = MagicMock()
            mock_win32security.ACL.return_value = MagicMock()
            mock_win32security.SetFileSecurity.return_value = None
            mock_win32api.GetComputerName.return_value = "TESTPC"

            # Set USERNAME environment variable to simulate potential spoofing
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ['USERNAME'] = 'SPOOFED_USER'

                try:
                    # Try to create Storage - should raise RuntimeError
                    # because GetUserName returned empty and we should NOT fall back to env var
                    with self.assertRaises(RuntimeError) as context:
                        Storage(path=os.path.join(tmpdir, "todos.json"))

                    # Verify the error message mentions username issue
                    self.assertIn("Unable to determine username", str(context.exception))
                finally:
                    # Clean up
                    if 'USERNAME' in os.environ:
                        del os.environ['USERNAME']

    def test_windows_whitespace_getusername_raises_error(self):
        """Test that whitespace-only GetUserName result raises RuntimeError."""
        if os.name != 'nt':
            self.skipTest("Windows-only test")

        # Mock win32api.GetUserName to return whitespace
        with patch('flywheel.storage.win32api') as mock_win32api, \
             patch('flywheel.storage.win32security') as mock_win32security, \
             patch('flywheel.storage.win32con'):

            # Make GetUserName return whitespace
            mock_win32api.GetUserName.return_value = "   "

            # Mock security setup functions
            mock_win32security.SECURITY_DESCRIPTOR.return_value = MagicMock()
            mock_win32security.ACL.return_value = MagicMock()
            mock_win32security.SetFileSecurity.return_value = None
            mock_win32api.GetComputerName.return_value = "TESTPC"

            # Set USERNAME environment variable
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ['USERNAME'] = 'SPOOFED_USER'

                try:
                    # Try to create Storage - should raise RuntimeError
                    with self.assertRaises(RuntimeError) as context:
                        Storage(path=os.path.join(tmpdir, "todos.json"))

                    # Verify the error message mentions username issue
                    self.assertIn("Unable to determine username", str(context.exception))
                finally:
                    # Clean up
                    if 'USERNAME' in os.environ:
                        del os.environ['USERNAME']


if __name__ == '__main__':
    unittest.main()

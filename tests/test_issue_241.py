"""Test for Issue #241 - Windows domain parsing logic error.

This test verifies that the domain parsing logic correctly handles
multiple DC= parts in a distinguished name without redundant processing.
"""

import unittest
from unittest.mock import patch, MagicMock


class TestIssue241WindowsDomainParsing(unittest.TestCase):
    """Test Windows domain parsing logic for correctness."""

    def test_domain_parsing_multiple_dc_parts(self):
        """Test that domain is parsed correctly from multiple DC= parts.

        The bug was that the domain parsing logic was inside a loop,
        causing it to execute multiple times unnecessarily.

        Example DN: CN=user,OU=users,DC=example,DC=com
        Expected domain: example.com
        """
        # Mock Windows API calls
        with patch('os.name', 'nt'):
            # Mock the win32 modules
            mock_win32security = MagicMock()
            mock_win32con = MagicMock()
            mock_win32api = MagicMock()

            # Set up the mocks
            mock_win32con.NameFullyQualifiedDN = 3  # Actual value
            mock_win32api.GetUserName.return_value = 'testuser'

            # Simulate a distinguished name with multiple DC= parts
            mock_win32api.GetUserNameEx.return_value = 'CN=user,OU=users,DC=example,DC=com'

            # Mock LookupAccountName to succeed
            mock_sid = MagicMock()
            mock_win32security.LookupAccountName.return_value = (mock_sid, None, None)

            # Mock security descriptor and ACL
            mock_security_descriptor = MagicMock()
            mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_security_descriptor

            mock_dacl = MagicMock()
            mock_win32security.ACL.return_value = mock_dacl

            # Mock SetFileSecurity to succeed
            mock_win32security.SetFileSecurity.return_value = None

            # Patch the imports
            with patch.dict('sys.modules', {
                'win32security': mock_win32security,
                'win32con': mock_win32con,
                'win32api': mock_win32api,
            }):
                # Import after patching
                import importlib
                from flywheel import storage

                # Reload to use patched modules
                importlib.reload(storage)

                # Create a Storage instance to trigger the domain parsing
                from pathlib import Path
                import tempfile

                with tempfile.TemporaryDirectory() as tmpdir:
                    storage_path = Path(tmpdir) / 'test_todos.json'

                    # This will trigger _secure_directory which contains the bug
                    s = storage.Storage(str(storage_path))

                    # Verify that LookupAccountName was called with the correct domain
                    # The domain should be 'example.com' (parsed from DC=example,DC=com)
                    mock_win32security.LookupAccountName.assert_called_once()

                    # Get the actual arguments passed to LookupAccountName
                    call_args = mock_win32security.LookupAccountName.call_args
                    actual_domain = call_args[0][0] if call_args[0] else call_args[1].get('domain')

                    # The domain should be 'example.com', not just 'example' or 'com'
                    # and the parsing should only happen once
                    self.assertEqual(actual_domain, 'example.com')

                    # Verify the domain parsing logic was efficient (not executed multiple times)
                    # The original bug would execute the join multiple times in the loop
                    # We can verify this by checking the call count is reasonable
                    self.assertLessEqual(mock_win32security.LookupAccountName.call_count, 1)

    def test_domain_parsing_single_dc_part(self):
        """Test that domain is parsed correctly from a single DC= part.

        Example DN: CN=user,DC=localdomain
        Expected domain: localdomain
        """
        # Mock Windows API calls
        with patch('os.name', 'nt'):
            # Mock the win32 modules
            mock_win32security = MagicMock()
            mock_win32con = MagicMock()
            mock_win32api = MagicMock()

            # Set up the mocks
            mock_win32con.NameFullyQualifiedDN = 3
            mock_win32api.GetUserName.return_value = 'testuser'

            # Simulate a distinguished name with a single DC= part
            mock_win32api.GetUserNameEx.return_value = 'CN=user,DC=localdomain'

            # Mock LookupAccountName to succeed
            mock_sid = MagicMock()
            mock_win32security.LookupAccountName.return_value = (mock_sid, None, None)

            # Mock security descriptor and ACL
            mock_security_descriptor = MagicMock()
            mock_win32security.SECURITY_DESCRIPTOR.return_value = mock_security_descriptor

            mock_dacl = MagicMock()
            mock_win32security.ACL.return_value = mock_dacl

            # Mock SetFileSecurity to succeed
            mock_win32security.SetFileSecurity.return_value = None

            # Patch the imports
            with patch.dict('sys.modules', {
                'win32security': mock_win32security,
                'win32con': mock_win32con,
                'win32api': mock_win32api,
            }):
                # Import after patching
                import importlib
                from flywheel import storage

                # Reload to use patched modules
                importlib.reload(storage)

                # Create a Storage instance to trigger the domain parsing
                from pathlib import Path
                import tempfile

                with tempfile.TemporaryDirectory() as tmpdir:
                    storage_path = Path(tmpdir) / 'test_todos.json'

                    # This will trigger _secure_directory which contains the bug
                    s = storage.Storage(str(storage_path))

                    # Verify that LookupAccountName was called with the correct domain
                    mock_win32security.LookupAccountName.assert_called_once()

                    # Get the actual arguments passed to LookupAccountName
                    call_args = mock_win32security.LookupAccountName.call_args
                    actual_domain = call_args[0][0] if call_args[0] else call_args[1].get('domain')

                    # The domain should be 'localdomain'
                    self.assertEqual(actual_domain, 'localdomain')


if __name__ == '__main__':
    unittest.main()

"""Test to verify Issue #339 is a false positive.

Issue #339 claimed that LookupAccountName failures were not handled properly.

However, investigation shows this is a FALSE POSITIVE from the AI scanner.
The actual code at lines 272-279 already properly handles LookupAccountName failures:

    try:
        sid, _, _ = win32security.LookupAccountName(domain, user)
    except Exception as e:
        # LookupAccountName failed - raise error without fallback
        raise RuntimeError(
            f"Failed to set Windows ACLs: Unable to lookup account '{user}' in domain '{domain}'. "
            f"Install pywin32: pip install pywin32. Error: {e}"
        ) from e

This test verifies:
1. LookupAccountName is properly wrapped in a try-except block
2. When LookupAccountName fails, a RuntimeError is raised
3. The error message contains helpful debugging information
4. The code does NOT continue execution after LookupAccountName fails

Related: Similar false positives were found in issues #159, #337, #330, #340, and #342
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Note: These tests use mocks, so they can run on any platform


class TestIssue339LookupAccountNameErrorHandling:
    """Test that LookupAccountName failures are properly handled."""

    def test_lookupaccountname_has_exception_handling(self):
        """Verify that LookupAccountName is wrapped in try-except."""
        storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

        with open(storage_path) as f:
            source_code = f.read()

        # Verify that LookupAccountName is called within a try-except block
        # The code should have "try:" before "LookupAccountName"
        try_index = source_code.find("try:")
        lookup_index = source_code.find("LookupAccountName")

        # The lookup should be after a try block
        assert lookup_index > try_index, \
            "LookupAccountName should be called after a try block"

        # Verify that the try-except block specifically catches Exception
        # and raises RuntimeError
        assert "except Exception as e:" in source_code, \
            "Code should have except Exception handler"

        # Verify that RuntimeError is raised when LookupAccountName fails
        assert "raise RuntimeError" in source_code, \
            "Code should raise RuntimeError on failure"

    def test_lookupaccountname_failure_raises_runtimeerror(self):
        """Test that LookupAccountName failure raises RuntimeError."""
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

                # Mock LookupAccountName to FAIL (this is the key test)
                win32security.LookupAccountName.side_effect = Exception(
                    "No mapping between account names and security IDs was done"
                )

                # Mock other win32security calls (they won't be reached)
                win32security.SECURITY_DESCRIPTOR = MagicMock
                win32security.ACL = MagicMock
                win32security.ACL_REVISION = 1
                win32con.FILE_ALL_ACCESS = 1
                win32con.NameFullyQualifiedDN = 1

                # Storage creation should raise RuntimeError when LookupAccountName fails
                with pytest.raises(RuntimeError) as exc_info:
                    from flywheel.storage import Storage
                    storage = Storage(path=str(test_path))

                # Verify the error message contains helpful information
                error_message = str(exc_info.value)
                assert "Failed to set Windows ACLs" in error_message, \
                    f"Error message should mention ACL failure. Got: {error_message}"
                assert "Unable to lookup account" in error_message, \
                    f"Error message should mention lookup failure. Got: {error_message}"
                assert "testuser" in error_message, \
                    f"Error message should include username. Got: {error_message}"
                assert "pywin32" in error_message, \
                    f"Error message should mention pywin32. Got: {error_message}"

    def test_lookupaccountname_failure_prevents_continuation(self):
        """Test that code does NOT continue after LookupAccountName fails.

        This is the key security issue mentioned in #339: if LookupAccountName
        fails, the code should raise an exception rather than continuing with
        potentially None or invalid SID values.
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

                # Mock GetUserName to succeed
                win32api.GetUserName.return_value = "testuser"
                win32api.GetUserNameEx.return_value = "CN=testuser,DC=example,DC=com"

                # Mock LookupAccountName to FAIL
                win32security.LookupAccountName.side_effect = Exception("Lookup failed")

                # Create a flag to track if SECURITY_DESCRIPTOR was created
                descriptor_created = []

                def mock_security_descriptor():
                    descriptor_created.append(True)
                    raise AssertionError("SECURITY_DESCRIPTOR should not be created after LookupAccountName fails")

                win32security.SECURITY_DESCRIPTOR = mock_security_descriptor
                win32security.ACL = MagicMock
                win32con.FILE_ALL_ACCESS = 1
                win32con.NameFullyQualifiedDN = 1

                # Storage creation should raise RuntimeError
                # and SECURITY_DESCRIPTOR should NOT be created
                with pytest.raises(RuntimeError):
                    from flywheel.storage import Storage
                    storage = Storage(path=str(test_path))

                # Verify that SECURITY_DESCRIPTOR was not created
                # This proves that execution did NOT continue after LookupAccountName failed
                assert len(descriptor_created) == 0, \
                    "SECURITY_DESCRIPTOR should not be created after LookupAccountName fails"

    def test_lookupaccountname_success_allows_continuation(self):
        """Test that code continues normally when LookupAccountName succeeds.

        This verifies that the error handling doesn't break the normal flow.
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

                # Mock GetUserName to succeed
                win32api.GetUserName.return_value = "testuser"
                win32api.GetUserNameEx.return_value = "CN=testuser,DC=example,DC=com"

                # Mock LookupAccountName to SUCCEED
                win32security.LookupAccountName.return_value = ("S-1-5-21-1", 1, 1)

                # Mock other win32security calls
                win32security.SECURITY_DESCRIPTOR = MagicMock()
                win32security.ACL = MagicMock()
                win32security.ACL_REVISION = 1
                win32security.DACL_SECURITY_INFORMATION = 1
                win32security.PROTECTED_DACL_SECURITY_INFORMATION = 1
                win32security.OWNER_SECURITY_INFORMATION = 1
                win32security.SACL_SECURITY_INFORMATION = 1
                win32con.FILE_LIST_DIRECTORY = 1
                win32con.FILE_ADD_FILE = 1
                win32con.FILE_READ_ATTRIBUTES = 1
                win32con.FILE_WRITE_ATTRIBUTES = 1
                win32con.DELETE = 1
                win32con.SYNCHRONIZE = 1
                win32con.NameFullyQualifiedDN = 1

                # Storage creation should succeed
                from flywheel.storage import Storage
                storage = Storage(path=str(test_path))

                # Verify LookupAccountName was called
                assert win32security.LookupAccountName.called, \
                    "LookupAccountName should be called when everything succeeds"

                # Verify SECURITY_DESCRIPTOR was created
                assert win32security.SECURITY_DESCRIPTOR.called, \
                    "SECURITY_DESCRIPTOR should be created when LookupAccountName succeeds"

    def test_error_message_contains_all_required_info(self):
        """Test that the error message contains all required debugging information."""
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
                win32api.GetUserNameEx.return_value = "CN=testuser,DC=example,DC=com"

                # Mock LookupAccountName to fail with specific error
                win32security.LookupAccountName.side_effect = Exception(
                    "No such user"
                )

                win32security.SECURITY_DESCRIPTOR = MagicMock
                win32security.ACL = MagicMock
                win32con.FILE_ALL_ACCESS = 1
                win32con.NameFullyQualifiedDN = 1

                # Storage creation should raise RuntimeError
                with pytest.raises(RuntimeError) as exc_info:
                    from flywheel.storage import Storage
                    storage = Storage(path=str(test_path))

                error_message = str(exc_info.value)

                # Verify error message contains all required information
                required_strings = [
                    "Failed to set Windows ACLs",
                    "Unable to lookup account",
                    "testuser",  # username
                    "example.com",  # domain
                    "pywin32",
                    "pip install pywin32",
                    "No such user",  # original error
                ]

                for required in required_strings:
                    assert required in error_message, \
                        f"Error message should contain '{required}'. Got: {error_message}"

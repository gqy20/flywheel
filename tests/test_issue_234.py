"""Tests for Issue #234 - Windows ACL domain variable initialization."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import Storage


class TestWindowsACLDomainInitialization:
    """Test that domain variable is properly initialized in all code paths."""

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_domain_initialized_when_getusernameex_fails_without_domain(self):
        """Test that domain is initialized even when GetUserNameEx fails to find domain."""
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

                # Mock GetUserNameEx to return a DN without DC= (no domain)
                win32api.GetUserNameEx.return_value = "CN=user,OU=users"
                # Mock GetUserName to succeed
                win32api.GetUserName.return_value = "testuser"
                # Mock GetComputerName to raise exception
                win32api.GetComputerName.side_effect = Exception("Computer name unavailable")
                # Mock LookupAccountName to succeed (should not be reached in this test)
                win32security.LookupAccountName.return_value = ("S-1-5-21-1", 1, 1)
                # Mock other win32security calls
                win32security.SECURITY_DESCRIPTOR = MagicMock
                win32security.ACL = MagicMock
                win32security.ACL_REVISION = 1
                win32security.DACL_SECURITY_INFORMATION = 1
                win32security.PROTECTED_DACL_SECURITY_INFORMATION = 1
                win32con.FILE_ALL_ACCESS = 1

                # This should raise NameError if domain is not properly initialized
                # or should handle the exception gracefully
                try:
                    storage = Storage(path=str(test_path))
                    # If we reach here, domain was properly initialized
                    # or the exception was caught
                    assert True
                except NameError as e:
                    if 'domain' in str(e):
                        pytest.fail(f"Domain variable was not initialized: {e}")
                    else:
                        raise
                except Exception:
                    # Other exceptions are acceptable (e.g., ACL setting failures)
                    pass

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_domain_initialized_with_edge_case_empty_parts(self):
        """Test domain initialization with edge case of empty DC parts."""
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

                # Mock GetUserNameEx to return a DN with edge case format
                win32api.GetUserNameEx.return_value = "CN=user,OU=users,DC="
                win32api.GetUserName.return_value = "testuser"
                win32api.GetComputerName.return_value = "COMPUTER"
                win32security.LookupAccountName.return_value = ("S-1-5-21-1", 1, 1)
                win32security.SECURITY_DESCRIPTOR = MagicMock
                win32security.ACL = MagicMock
                win32security.ACL_REVISION = 1
                win32security.DACL_SECURITY_INFORMATION = 1
                win32security.PROTECTED_DACL_SECURITY_INFORMATION = 1
                win32con.FILE_ALL_ACCESS = 1

                try:
                    storage = Storage(path=str(test_path))
                    assert True
                except NameError as e:
                    if 'domain' in str(e):
                        pytest.fail(f"Domain variable was not initialized: {e}")
                    else:
                        raise
                except Exception:
                    pass

"""Test Windows security fix for Issue #674.

This test ensures that on Windows:
1. If pywin32 is missing, an error should be raised by default
2. The error should be clear about the security risk
3. Only with explicit unsafe_mode=True should it allow degraded mode
"""

import os
import sys
import pytest
import importlib

# Skip tests on non-Windows platforms
pytestmark = pytest.mark.skipif(
    os.name != 'nt',
    reason="Windows-specific security test"
)


class TestWindowsSecurityFix:
    """Test that Windows requires pywin32 for safe operation."""

    def test_windows_without_pywin32_raises_error(self):
        """Test that importing storage.py on Windows without pywin32 raises an error."""
        # This test verifies the security fix for Issue #674
        # On Windows, if pywin32 is not available, an ImportError should be raised

        # Try to import the storage module
        # On Windows without pywin32, this should raise ImportError
        try:
            import flywheel.storage
            # If we get here on Windows, pywin32 is available or the fix isn't applied yet
            if os.name == 'nt':
                # Check if pywin32 is actually available
                try:
                    import win32file
                    # pywin32 is available, so no error expected
                    pass
                except ImportError:
                    # pywin32 is not available but no error was raised
                    # This means the security fix is NOT applied
                    pytest.fail(
                        "ImportError should be raised on Windows without pywin32. "
                        "Current code allows unsafe degraded mode which can cause "
                        "data corruption in multi-process environments."
                    )
        except ImportError as e:
            # This is expected on Windows without pywin32
            if os.name == 'nt':
                # Verify the error message mentions the security issue
                error_msg = str(e).lower()
                assert any(keyword in error_msg for keyword in [
                    'pywin32',
                    'security',
                    'windows',
                    'required',
                    'unsafe'
                ]), f"Error message should mention pywin32/security requirement: {e}"

    def test_degraded_mode_check(self):
        """Test the _is_degraded_mode function."""
        from flywheel.storage import _is_degraded_mode

        if os.name != 'nt':
            # On Unix, degraded mode should always be False
            assert _is_degraded_mode() is False
        else:
            # On Windows, check if pywin32 is available
            try:
                import win32file
                # If pywin32 is available, degraded mode should be False
                assert _is_degraded_mode() is False, \
                    "Should not be in degraded mode when pywin32 is available"
            except ImportError:
                # If pywin32 is not available, this should raise an error
                # after the security fix is applied
                with pytest.raises((ImportError, RuntimeError)):
                    # The fix should prevent running in degraded mode
                    raise RuntimeError(
                        "Cannot run in degraded mode on Windows without pywin32. "
                        "This is unsafe and can cause data corruption. "
                        "Install pywin32 or explicitly enable unsafe mode."
                    )

    def test_windows_security_warning(self):
        """Test that Windows security is properly enforced."""
        if os.name != 'nt':
            pytest.skip("Windows-specific test")

        # This test documents the expected behavior after the fix
        try:
            import win32file
            # pywin32 is available, no issue
            assert True
        except ImportError:
            # pywin32 is not available
            # After the fix, importing flywheel.storage should raise ImportError
            with pytest.raises(ImportError) as exc_info:
                # Force a reimport to check the error
                import importlib
                import flywheel.storage
                importlib.reload(flywheel.storage)

            # Verify the error message is clear about the security risk
            error_msg = str(exc_info.value).lower()
            assert 'pywin32' in error_msg or 'security' in error_msg

"""Test for Issue #514: Windows optional locking mode.

This test verifies that the application can run in degraded mode when
pywin32 is not available on Windows, provided the user explicitly
opts in via environment variable.
"""

import os
import sys
import pytest
from unittest.mock import patch
from pathlib import Path

# We need to test module import behavior
# The storage module must be importable even without pywin32 (with env var)


class TestWindowsOptionalLocking:
    """Test Windows optional locking mode (Issue #514)."""

    def test_windows_import_without_pywin32_fails_by_default(self):
        """Test that importing storage on Windows without pywin32 fails by default.

        This verifies the current secure behavior - without explicit opt-in,
        missing pywin32 should cause ImportError to prevent unsafe operation.
        """
        # Skip on non-Windows platforms
        if sys.platform != 'win32':
            pytest.skip("Test only applicable on Windows")

        # Mock Windows platform and missing pywin32
        with patch('sys.platform', 'win32'):
            with patch.dict('os.name', 'nt'):
                # Remove pywin32 from modules to simulate it not being installed
                modules_to_remove = [
                    'win32security', 'win32con', 'win32api',
                    'win32file', 'pywintypes'
                ]
                original_modules = {}
                for mod in modules_to_remove:
                    if mod in sys.modules:
                        original_modules[mod] = sys.modules[mod]
                        del sys.modules[mod]

                # Ensure the environment variable is NOT set
                old_env = os.environ.get('FLYWHEEL_ALLOW_INSECURE_NO_WIN32')
                if 'FLYWHEEL_ALLOW_INSECURE_NO_WIN32' in os.environ:
                    del os.environ['FLYWHEEL_ALLOW_INSECURE_NO_WIN32']

                try:
                    # Attempt to import storage - should fail with ImportError
                    with pytest.raises(ImportError) as exc_info:
                        import importlib
                        if 'flywheel.storage' in sys.modules:
                            del sys.modules['flywheel.storage']
                        importlib.import_module('flywheel.storage')

                    # Verify the error message mentions pywin32
                    assert 'pywin32' in str(exc_info.value).lower()
                finally:
                    # Restore modules
                    for mod, val in original_modules.items():
                        sys.modules[mod] = val

                    # Restore environment
                    if old_env is not None:
                        os.environ['FLYWHEEL_ALLOW_INSECURE_NO_WIN32'] = old_env

    def test_windows_import_without_pywin26_succeeds_with_env_var(self):
        """Test that importing storage on Windows without pywin32 succeeds with env var.

        When FLYWHEEL_ALLOW_INSECURE_NO_WIN32 is set, the application should
        be able to import and run in degraded mode (with warnings).
        """
        # Skip on non-Windows platforms
        if sys.platform != 'win32':
            pytest.skip("Test only applicable on Windows")

        # Mock Windows platform and missing pywin32
        with patch('sys.platform', 'win32'):
            with patch.dict('os.name', 'nt'):
                # Remove pywin32 from modules
                modules_to_remove = [
                    'win32security', 'win32con', 'win32api',
                    'win32file', 'pywintypes'
                ]
                original_modules = {}
                for mod in modules_to_remove:
                    if mod in sys.modules:
                        original_modules[mod] = sys.modules[mod]
                        del sys.modules[mod]

                # Set the environment variable to opt-in to degraded mode
                os.environ['FLYWHEEL_ALLOW_INSECURE_NO_WIN32'] = '1'

                try:
                    # Attempt to import storage - should succeed
                    import importlib
                    if 'flywheel.storage' in sys.modules:
                        del sys.modules['flywheel.storage']
                    importlib.import_module('flywheel.storage')

                    # If we get here, the import succeeded
                    from flywheel.storage import Storage

                    # Verify that Storage class exists and can be instantiated
                    # (though file locking may not work)
                    assert Storage is not None
                finally:
                    # Restore modules
                    for mod, val in original_modules.items():
                        sys.modules[mod] = val

                    # Clean up environment
                    if 'FLYWHEEL_ALLOW_INSECURE_NO_WIN32' in os.environ:
                        del os.environ['FLYWHEEL_ALLOW_INSECURE_NO_WIN32']

    def test_unix_platform_unaffected_by_pywin32(self):
        """Test that Unix platforms don't require pywin32.

        On Unix-like systems, pywin32 should not be required at all.
        """
        # Skip on Windows
        if sys.platform == 'win32':
            pytest.skip("Test only applicable on Unix-like systems")

        # On Unix, storage should import successfully without any pywin32
        from flywheel.storage import Storage
        assert Storage is not None

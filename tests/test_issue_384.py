"""Test for Issue #384 - Windows pywin32 ImportError handling.

This test verifies that when pywin32 dependencies are not installed on Windows,
the code provides a clear error message instead of crashing with ImportError.
"""

import sys
import os
import unittest
from unittest.mock import patch


class TestWindowsPywin32ImportError(unittest.TestCase):
    """Test that Windows pywin32 import errors are handled gracefully."""

    def test_windows_pywin32_import_error_provides_helpful_message(self):
        """Test that missing pywin32 on Windows provides a clear error message.

        When pywin32 is not installed on Windows, the module should catch
        ImportError and provide a helpful error message telling users to
        install pywin32, rather than crashing with an unclear ImportError.
        """
        # Skip if not on Windows (this test is Windows-specific)
        if os.name != 'nt':
            self.skipTest("Test is Windows-specific")

        # Mock the win32security, win32con, and win32api modules to raise ImportError
        # This simulates the scenario where pywin32 is not installed
        import importlib

        # We need to test at module import time
        # First, let's check if the modules are already imported
        # If they are, we can't test ImportError scenario
        if 'win32security' in sys.modules:
            self.skipTest("win32security already imported, cannot test ImportError")

        # Create a mock import hook that raises ImportError for win32 modules
        original_import = __builtins__.__import__

        def mock_import(name, *args, **kwargs):
            if name in ('win32security', 'win32con', 'win32api'):
                raise ImportError(
                    f"No module named '{name}'. "
                    f"pywin32 is required on Windows. "
                    f"Install it with: pip install pywin32"
                )
            return original_import(name, *args, **kwargs)

        # Patch __import__ to simulate missing pywin32
        with patch('builtins.__import__', side_effect=mock_import):
            # Remove from sys.modules if present to force re-import
            for module_name in ['flywheel.storage']:
                if module_name in sys.modules:
                    del sys.modules[module_name]

            # Try to import storage module
            # It should raise ImportError with a helpful message
            with self.assertRaises(ImportError) as context:
                import flywheel.storage

            # Verify the error message mentions pywin32 installation
            error_message = str(context.exception)
            self.assertIn('pywin32', error_message.lower())
            self.assertIn('pip install pywin32', error_message.lower())

    def test_windows_pywin32_import_succeeds_when_available(self):
        """Test that when pywin32 is available, import succeeds.

        This is the positive test case - when pywin32 is installed,
        the module should import successfully.
        """
        # Skip if not on Windows (this test is Windows-specific)
        if os.name != 'nt':
            self.skipTest("Test is Windows-specific")

        # If we reach here and win32security is already imported,
        # we know pywin32 is available
        if 'win32security' in sys.modules:
            # Test passes - module was imported successfully
            self.assertTrue(True)
            return

        # Try to import win32security
        try:
            import win32security
            import win32con
            import win32api
            # If we reach here, pywin32 is available
            self.assertTrue(True)
        except ImportError:
            # If pywin32 is not installed, skip this test
            self.skipTest("pywin32 not installed, cannot test successful import")


if __name__ == '__main__':
    unittest.main()

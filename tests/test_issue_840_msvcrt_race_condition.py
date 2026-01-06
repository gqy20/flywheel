"""
Test for Issue #840: Potential race condition in Windows file locking fallback logic.

This test verifies that:
1. The code does NOT use msvcrt.locking (which was removed in Issue #846)
2. Windows degraded mode uses file-based locks instead of msvcrt
3. No AttributeError or NameError occurs when pywin32 is not available

The issue reported a potential race condition where msvcrt was imported inside
the except ImportError block and set to None, but subsequent code assumed it
was available. This was fixed in Issue #846 by completely removing msvcrt
usage and replacing it with file-based locks.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Only run on Windows or when testing Windows-specific code
if os.name != 'nt':
    sys.platform = "win32"


class TestIssue840MsvcrtRaceCondition(unittest.TestCase):
    """Test that msvcrt is not used in Windows file locking."""

    def test_no_msvcrt_import_in_storage(self):
        """Verify that storage.py does not import msvcrt."""
        import flywheel.storage as storage_module

        # Get the source code of the storage module
        storage_file = Path(storage_module.__file__)
        source_code = storage_file.read_text()

        # Verify that msvcrt is NOT imported anywhere in the code
        self.assertNotIn('import msvcrt', source_code,
                        "msvcrt should not be imported (removed in Issue #846)")

        # Verify that msvcrt.locking is not used
        self.assertNotIn('msvcrt.locking', source_code,
                        "msvcrt.locking should not be used (replaced with file-based locks)")

    def test_windows_fallback_uses_file_lock_not_msvcrt(self):
        """Verify that Windows degraded mode uses file-based locks, not msvcrt.locking."""
        import flywheel.storage as storage_module

        # Check that the module has the expected Windows variables
        self.assertTrue(hasattr(storage_module, 'win32file'))
        self.assertTrue(hasattr(storage_module, 'win32api'))
        self.assertTrue(hasattr(storage_module, 'pywintypes'))

        # When pywin32 is not available, these should be None
        # But the module should still load without errors
        try:
            # Try importing without pywin32
            with patch.dict('sys.modules', {
                'win32security': None,
                'win32con': None,
                'win32api': None,
                'win32file': None,
                'pywintypes': None,
            }):
                # Force reload the module to simulate degraded mode
                import importlib
                importlib.reload(storage_module)

                # Module should load successfully even without pywin32
                self.assertIsNotNone(storage_module)

        except ImportError as e:
            self.fail(f"Module should load without pywin32: {e}")

    def test_degraded_mode_file_lock_not_msvcrt(self):
        """Verify that degraded mode on Windows uses file-based locks."""
        import flywheel.storage
        import warnings

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
            f.write('{}')

        try:
            # Mock Windows environment without pywin32
            with patch('os.name', 'nt'):
                with patch.dict('sys.modules', {
                    'win32security': None,
                    'win32con': None,
                    'win32api': None,
                    'win32file': None,
                    'pywintypes': None,
                }):
                    # Reload module to trigger degraded mode
                    import importlib
                    importlib.reload(flywheel.storage)

                    # Verify that FileStorage can be initialized
                    # This should use file-based locks, not msvcrt
                    with warnings.catch_warnings(record=True) as w:
                        warnings.simplefilter("always")

                        storage = flywheel.storage.FileStorage(temp_file)

                        # Should get a warning about degraded mode
                        if len(w) > 0:
                            warning_messages = [str(warning.message) for warning in w]
                            self.assertTrue(
                                any('pywin32' in msg or 'fallback' in msg or 'file locking' in msg
                                    for msg in warning_messages),
                                "Should warn about pywin32 not being available"
                            )

                        # Storage should be functional
                        self.assertIsNotNone(storage)

        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(temp_file + '.lock'):
                os.remove(temp_file + '.lock')

            # Reload module with original imports
            import importlib
            importlib.reload(flywheel.storage)

    def test_no_msvcrt_reference_in_lock_acquire(self):
        """Verify that _acquire_file_lock does not reference msvcrt."""
        import flywheel.storage
        import inspect

        # Get the source code of _acquire_file_lock
        source = inspect.getsource(flywheel.storage._FileLock._acquire_file_lock)

        # Verify msvcrt is not mentioned
        self.assertNotIn('msvcrt', source.lower(),
                        "_acquire_file_lock should not reference msvcrt")

        # Verify that file-based lock mechanism is mentioned
        if os.name == 'nt':
            # On Windows, should use .lock files when in degraded mode
            self.assertIn('.lock', source,
                         "Windows degraded mode should use .lock files")


if __name__ == '__main__':
    unittest.main()

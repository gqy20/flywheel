"""Test for issue #401: Windows security modules should use lazy imports.

This test verifies that the storage module can be imported even when
pywin32 is not available on Windows. The security modules should be
imported lazily (when actually needed) rather than at module level.
"""

import sys
import importlib
from unittest.mock import patch
import pytest


class TestLazyImportIssue401:
    """Test lazy import of Windows security modules."""

    def test_storage_module_imports_without_pywin32_on_windows(self):
        """Test that storage module can be imported on Windows even if pywin32 is missing.

        This is a regression test for issue #401. The module should use lazy imports
        for Windows security modules so it can be imported as a library even when
        pywin32 is not installed.
        """
        # Mock os.name to simulate Windows
        # Mock the pywin32 modules to raise ImportError
        mock_modules = {
            'win32security': ImportError('No module named win32security'),
            'win32con': ImportError('No module named win32con'),
            'win32api': ImportError('No module named win32api'),
            'win32file': ImportError('No module named win32file'),
        }

        # Create a mock import function that raises ImportError for pywin32 modules
        original_import = __builtins__.__import__

        def mock_import(name, *args, **kwargs):
            if name in mock_modules:
                raise mock_modules[name]
            return original_import(name, *args, **kwargs)

        # Remove storage module from sys.modules if it was already imported
        if 'flywheel.storage' in sys.modules:
            del sys.modules['flywheel.storage']

        with patch('sys.modules', {'os.name': 'nt'}):
            with patch('builtins.__import__', side_effect=mock_import):
                with patch('os.name', 'nt'):
                    # This should NOT raise ImportError at module level
                    # The import should only fail when actually trying to use
                    # Windows-specific security features
                    try:
                        import flywheel.storage
                        # If we get here, lazy imports are working correctly
                        assert True, "Module imported successfully without pywin32"
                    except ImportError as e:
                        # This is the bug - module raises ImportError at import time
                        pytest.fail(
                            f"storage module should be importable without pywin32 on Windows. "
                            f"Got ImportError: {e}"
                        )

    def test_storage_raises_error_when_using_security_without_pywin32(self):
        """Test that using security features without pywin32 raises an error.

        While the module should be importable without pywin32, actually using
        Windows security features should fail gracefully with a clear error.
        """
        # This test verifies that when you actually try to USE security features
        # without pywin32, you get a proper error message (not an ImportError)

        # We can't easily test this on non-Windows systems, but the test structure
        # is here for when running on Windows or with proper mocking
        if sys.platform != 'win32':
            pytest.skip("This test only runs on Windows")

        # Mock the pywin32 imports to fail
        with patch.dict('sys.modules', {
            'win32security': None,
            'win32con': None,
            'win32api': None,
            'win32file': None,
        }):
            # Reimport storage to trigger the import failure
            if 'flywheel.storage' in sys.modules:
                del sys.modules['flywheel.storage']

            import flywheel.storage

            # Trying to create a Storage object should fail with a clear error
            # about missing pywin32, not a cryptic ImportError
            with pytest.raises(RuntimeError) as exc_info:
                storage = flywheel.storage.Storage()

            assert 'pywin32' in str(exc_info.value).lower()

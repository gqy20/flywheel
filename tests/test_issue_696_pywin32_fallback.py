"""Test that module gracefully handles missing pywin32 on Windows (Issue #696).

Issue #696: On Windows, if pywin32 is not installed, the module import raises
ImportError directly, preventing the program from starting. While comments mention
this is for security (Issue #674), it breaks code portability.

The fix should provide a fallback to a slower but safe pure Python file lock
implementation, rather than crashing immediately.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest


class TestIssue696Pywin32Fallback:
    """Test graceful handling of missing pywin32 on Windows.

    Issue #696: When pywin32 is not installed on Windows, the module should
    fall back to a safe pure Python implementation rather than raising ImportError.
    """

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_module_imports_without_pywin32_on_windows(self):
        """Test that the module can be imported even without pywin32 on Windows.

        This test simulates the scenario where pywin32 is not installed on Windows.
        The module should use a fallback implementation instead of raising ImportError.
        """
        # We need to test that the module can handle missing pywin32 gracefully
        # This is done by mocking the import of pywin32 modules to fail

        # Remove the module from sys.modules if it was already imported
        modules_to_remove = [
            'flywheel.storage',
            'flywheel',
        ]
        removed_modules = {}
        for mod in modules_to_remove:
            if mod in sys.modules:
                removed_modules[mod] = sys.modules.pop(mod)

        try:
            # Mock the pywin32 imports to fail
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name in ['win32security', 'win32con', 'win32api', 'win32file', 'pywintypes']:
                    raise ImportError(f"No module named '{name}'")
                return original_import(name, *args, **kwargs)

            with patch('builtins.__import__', side_effect=mock_import):
                # Try to import the module - it should not raise ImportError
                # Instead, it should use a fallback implementation
                try:
                    import importlib
                    # Force re-import
                    if 'flywheel.storage' in sys.modules:
                        del sys.modules['flywheel.storage']
                    storage_module = importlib.import_module('flywheel.storage')

                    # If we get here without ImportError, the fix is working
                    # The module should have set up some kind of fallback mode
                    assert storage_module is not None

                    # Check that _is_degraded_mode returns True when pywin32 is missing
                    # This would indicate the fallback is active
                    degraded_mode = storage_module._is_degraded_mode()
                    assert degraded_mode is True, (
                        "When pywin32 is not available on Windows, "
                        "the module should enter degraded mode instead of raising ImportError"
                    )

                except ImportError as e:
                    pytest.fail(
                        f"Module raised ImportError when pywin32 is missing on Windows. "
                        f"This breaks code portability. "
                        f"Error: {e}"
                    )
        finally:
            # Restore removed modules
            for mod, module in removed_modules.items():
                sys.modules[mod] = module

    def test_is_degraded_mode_reflects_pywin32_availability(self):
        """Test that _is_degraded_mode returns correct value based on pywin32 availability.

        This test verifies that:
        1. On Windows with pywin32: returns False (normal mode)
        2. On Windows without pywin32: returns True (degraded mode)
        3. On Unix systems: returns False (normal mode, uses fcntl)
        """
        from flywheel.storage import _is_degraded_mode

        if os.name == 'nt':  # Windows
            try:
                import win32file
                # pywin32 is available, should be in normal mode
                assert _is_degraded_mode() is False, (
                    "On Windows with pywin32 available, should not be in degraded mode"
                )
            except ImportError:
                # pywin32 is not available, should be in degraded mode
                assert _is_degraded_mode() is True, (
                    "On Windows without pywin32, should be in degraded mode"
                )
        else:
            # On Unix systems, should not be in degraded mode
            assert _is_degraded_mode() is False, (
                "On Unix systems, should not be in degraded mode"
            )

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_storage_backend_works_without_pywin32(self):
        """Test that storage backend can create instances even without pywin32.

        This is a functional test to ensure that when pywin32 is missing,
        the storage backend can still create instances and operate in degraded mode.
        """
        from flywheel.storage import FileStorage

        # Try to create a FileStorage instance
        # This should not raise ImportError even if pywin32 is missing
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                storage = FileStorage(tmpdir)
                assert storage is not None
            except ImportError as e:
                pytest.fail(
                    f"FileStorage raised ImportError when pywin32 is missing. "
                    f"The module should use a fallback implementation. Error: {e}"
                )

"""Tests for Issue #519: Insecure fallback on Windows.

This test ensures that:
1. The insecure environment variable FLYWHEEL_ALLOW_INSECURE_NO_WIN32 is removed
2. Only FLYWHEEL_DEBUG can bypass security requirements (for development/debugging)
3. By default, missing pywin32 on Windows should fail fast with ImportError
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

from flywheel.storage import Storage


class TestIssue519SecurityEnvVar(unittest.TestCase):
    """Test that insecure fallback is only allowed with explicit debug flag."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "todos.json"

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_windows_without_pywin32_should_fail_by_default(self):
        """Test that missing pywin32 on Windows fails fast by default."""
        # Mock Windows platform and make pywin32 import fail
        with patch('flywheel.storage.os.name', 'nt'):
            # Ensure no debug flags are set
            env = os.environ.copy()
            env.pop('FLYWHEEL_ALLOW_INSECURE_NO_WIN32', None)
            env.pop('FLYWHEEL_DEBUG', None)

            with patch.dict(os.environ, env, clear=False):
                # Mock import to fail for pywin32 modules
                import builtins
                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    if name.startswith('win32') or name == 'pywintypes':
                        raise ImportError(f"No module named '{name}'")
                    return original_import(name, *args, **kwargs)

                with patch('builtins.__import__', side_effect=mock_import):
                    # Re-import the module to trigger the ImportError
                    import importlib
                    import flywheel.storage
                    importlib.reload(flywheel.storage)

                    # Attempting to use Storage should fail with ImportError
                    # (because the module import should have failed)
                    with self.assertRaises(ImportError) as context:
                        from flywheel.storage import Storage
                        Storage(path=str(self.storage_path))

                    # Verify the error message mentions pywin32
                    error_msg = str(context.exception).lower()
                    self.assertIn("pywin32", error_msg)
                    self.assertIn("required", error_msg)

    def test_allow_insecure_env_var_should_not_work(self):
        """Test that FLYWHEEL_ALLOW_INSECURE_NO_WIN32 no longer works."""
        # Mock Windows platform
        with patch('flywheel.storage.os.name', 'nt'):
            # Set the OLD insecure environment variable
            env = os.environ.copy()
            env['FLYWHEEL_ALLOW_INSECURE_NO_WIN32'] = 'true'
            env.pop('FLYWHEEL_DEBUG', None)

            with patch.dict(os.environ, env, clear=False):
                # Mock import to fail for pywin32 modules
                import builtins
                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    if name.startswith('win32') or name == 'pywintypes':
                        raise ImportError(f"No module named '{name}'")
                    return original_import(name, *args, **kwargs)

                with patch('builtins.__import__', side_effect=mock_import):
                    # Re-import the module
                    import importlib
                    import flywheel.storage
                    importlib.reload(flywheel.storage)

                    # Even with the old env var set, it should still fail
                    # because the old variable should no longer be supported
                    with self.assertRaises(ImportError) as context:
                        from flywheel.storage import Storage
                        Storage(path=str(self.storage_path))

                    error_msg = str(context.exception).lower()
                    self.assertIn("pywin32", error_msg)

    def test_debug_flag_allows_degraded_mode(self):
        """Test that FLYWHEEL_DEBUG allows degraded mode for development."""
        # Mock Windows platform
        with patch('flywheel.storage.os.name', 'nt'):
            # Set the DEBUG flag
            env = os.environ.copy()
            env['FLYWHEEL_DEBUG'] = '1'
            env.pop('FLYWHEEL_ALLOW_INSECURE_NO_WIN32', None)

            with patch.dict(os.environ, env, clear=False):
                # Mock import to fail for pywin32 modules
                import builtins
                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    if name.startswith('win32') or name == 'pywintypes':
                        raise ImportError(f"No module named '{name}'")
                    return original_import(name, *args, **kwargs)

                with patch('builtins.__import__', side_effect=mock_import):
                    # Re-import the module
                    import importlib
                    import flywheel.storage
                    importlib.reload(flywheel.storage)

                    # With DEBUG flag, Storage should be creatable in degraded mode
                    # (This test documents the expected behavior after the fix)
                    # For now, this will fail because we haven't implemented the fix yet
                    try:
                        storage = Storage(path=str(self.storage_path))
                        # If we get here, the fix is implemented
                        self.assertIsNotNone(storage)
                    except ImportError:
                        # This is expected BEFORE the fix is applied
                        # After the fix, this should not raise ImportError when DEBUG is set
                        self.fail("FLYWHEEL_DEBUG should allow degraded mode, but it doesn't yet")


if __name__ == '__main__':
    unittest.main()

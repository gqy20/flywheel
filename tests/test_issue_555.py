"""Test for degraded mode Windows module handling (Issue #555).

Issue #555: Windows module import失败时，`win32security` 等变量可能为 None，
但在 `_secure_all_parent_directories` 中未检查 `_is_degraded_mode` 就直接使用，
会导致 AttributeError。
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import Storage


class TestIssue555DegradedModeHandling:
    """Test that degraded mode is properly checked before using Windows modules."""

    def test_secure_all_parent_directories_in_degraded_mode(self):
        """Test that _secure_all_parent_directories handles degraded mode gracefully.

        When pywin32 modules are None (degraded mode), calling
        _secure_all_parent_directories should not attempt to use None modules,
        which would cause AttributeError.

        This test ensures the method checks _is_degraded_mode() before trying
        to use win32api or other Windows-specific modules.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "subdir" / "test.todos.json"

            # Mock Windows environment
            with patch('os.name', 'nt'):
                # Mock the storage module's Windows modules as None (degraded mode)
                with patch('flywheel.storage.win32security', None):
                    with patch('flywheel.storage.win32con', None):
                        with patch('flywheel.storage.win32api', None):
                            with patch('flywheel.storage.win32file', None):
                                with patch('flywheel.storage.pywintypes', None):
                                    # Import the module again to pick up the mocked modules
                                    if 'flywheel.storage' in sys.modules:
                                        del sys.modules['flywheel.storage']

                                    from flywheel import storage

                                    # Mock _is_degraded_mode to return True
                                    with patch.object(storage, '_is_degraded_mode', return_value=True):
                                        # This should not raise AttributeError
                                        # Even though win32api is None, the method should
                                        # check _is_degraded_mode() and skip Windows-specific code
                                        try:
                                            s = Storage(str(test_path))
                                            # If we get here without AttributeError, the fix works
                                            assert s.path == test_path
                                        except AttributeError as e:
                                            if "NoneType" in str(e):
                                                pytest.fail(
                                                    f"AttributeError raised when using None Windows modules: {e}. "
                                                    "The code should check _is_degraded_mode() before using win32api."
                                                )
                                            else:
                                                raise

    def test_secure_directory_in_degraded_mode(self):
        """Test that _secure_directory handles degraded mode gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.todos.json"

            # Mock Windows environment
            with patch('os.name', 'nt'):
                # Mock the storage module's Windows modules as None (degraded mode)
                with patch('flywheel.storage.win32security', None):
                    with patch('flywheel.storage.win32con', None):
                        with patch('flywheel.storage.win32api', None):
                            with patch('flywheel.storage.win32file', None):
                                with patch('flywheel.storage.pywintypes', None):
                                    # Import the module again to pick up the mocked modules
                                    if 'flywheel.storage' in sys.modules:
                                        del sys.modules['flywheel.storage']

                                    from flywheel import storage

                                    # Create a storage instance
                                    s = Storage(str(test_path))

                                    # Mock _is_degraded_mode to return True
                                    with patch.object(storage, '_is_degraded_mode', return_value=True):
                                        # _secure_directory should handle degraded mode
                                        # It should either skip Windows security or use fallback
                                        try:
                                            s._secure_directory(test_path.parent)
                                            # If we get here, degraded mode is handled properly
                                        except AttributeError as e:
                                            if "NoneType" in str(e):
                                                pytest.fail(
                                                    f"_secure_directory raised AttributeError with None modules: {e}"
                                                )
                                            else:
                                                raise

    def test_initialization_respects_degraded_mode(self):
        """Test that Storage initialization works in degraded mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "subdir" / "test.todos.json"

            # Mock Windows environment
            with patch('os.name', 'nt'):
                # Mock the storage module's Windows modules as None (degraded mode)
                with patch('flywheel.storage.win32security', None):
                    with patch('flywheel.storage.win32con', None):
                        with patch('flywheel.storage.win32api', None):
                            with patch('flywheel.storage.win32file', None):
                                with patch('flywheel.storage.pywintypes', None):
                                    # Import the module again to pick up the mocked modules
                                    if 'flywheel.storage' in sys.modules:
                                        del sys.modules['flywheel.storage']

                                    from flywheel import storage

                                    # Mock _is_degraded_mode to return True
                                    with patch.object(storage, '_is_degraded_mode', return_value=True):
                                        # Storage initialization should work in degraded mode
                                        try:
                                            s = Storage(str(test_path))
                                            assert s.path == test_path
                                        except AttributeError as e:
                                            if "NoneType" in str(e) and "win32" in str(e).lower():
                                                pytest.fail(
                                                    f"Storage initialization failed in degraded mode: {e}. "
                                                    "The code should check _is_degraded_mode() before using Windows modules."
                                                )
                                            else:
                                                raise

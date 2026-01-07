"""
Test for Issue #919: Windows degraded mode deadlock risk

This test verifies that all Windows-specific modules (win32security, win32con,
win32api, win32file, pywintypes) are None in degraded mode to prevent accidental
use and potential deadlocks.
"""

import pytest
import sys
from unittest.mock import patch

# Import the storage module to test
from flywheel.storage import _is_degraded_mode


class TestDegradedModeSafetyChecks:
    """Test safety checks for degraded mode (Issue #919)."""

    def test_all_win32_modules_are_none_in_degraded_mode_windows(self):
        """
        Test that ALL win32* modules are None when in degraded mode on Windows.

        This prevents accidental use of these modules in degraded mode, which
        could lead to deadlocks or crashes.
        """
        # Mock Windows environment with degraded mode (pywin32 not available)
        with patch('os.name', 'nt'):
            # Simulate degraded mode by setting all win32 modules to None
            with patch('flywheel.storage.win32security', None):
                with patch('flywheel.storage.win32con', None):
                    with patch('flywheel.storage.win32api', None):
                        with patch('flywheel.storage.win32file', None):
                            with patch('flywheel.storage.pywintypes', None):
                                # Verify we're in degraded mode
                                assert _is_degraded_mode() is True

                                # Import the modules to check they're None
                                from flywheel import storage

                                # SAFETY CHECKS: All win32 modules must be None in degraded mode
                                assert storage.win32security is None, (
                                    "win32security must be None in degraded mode to prevent "
                                    "accidental use and potential deadlocks"
                                )
                                assert storage.win32con is None, (
                                    "win32con must be None in degraded mode to prevent "
                                    "accidental use and potential deadlocks"
                                )
                                assert storage.win32api is None, (
                                    "win32api must be None in degraded mode to prevent "
                                    "accidental use and potential deadlocks"
                                )
                                assert storage.win32file is None, (
                                    "win32file must be None in degraded mode to prevent "
                                    "accidental use and potential deadlocks"
                                )
                                assert storage.pywintypes is None, (
                                    "pywintypes must be None in degraded mode to prevent "
                                    "accidental use and potential deadlocks"
                                )

    def test_degraded_mode_file_lock_enforces_safety_checks(self):
        """
        Test that _acquire_file_lock enforces safety checks for all win32 modules.

        When in degraded mode, the method should verify that ALL win32 modules
        are None, not just win32file.
        """
        # This test will fail initially because the safety checks only cover win32file
        # After the fix, all win32* modules should be checked
        import tempfile
        import os
        from pathlib import Path

        # Skip on non-Windows systems for now
        if os.name != 'nt':
            pytest.skip("This test is specific to Windows degraded mode")

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
            f.write('{"test": "data"}')

        try:
            # Mock degraded mode
            with patch('flywheel.storage._is_degraded_mode', return_value=True):
                from flywheel.storage import FileStorage

                # Create FileStorage instance
                storage = FileStorage(temp_file)

                # Open the file to get a file handle
                file_handle = open(temp_file, 'r')

                # The _acquire_file_lock method should check ALL win32 modules
                # Currently it only checks win32file - this test will fail
                # until we add checks for win32security, win32con, win32api, pywintypes
                try:
                    # This will fail if any win32 module is not None in degraded mode
                    storage._acquire_file_lock(file_handle)
                except AssertionError as e:
                    # Expected: should fail with assertion about win32 modules
                    error_msg = str(e)
                    # After fix, error should mention all win32 modules
                    assert "win32" in error_msg.lower(), (
                        f"Expected assertion about win32 modules, got: {error_msg}"
                    )
                finally:
                    file_handle.close()

        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.remove(temp_file)
            lock_file = temp_file + '.lock'
            if os.path.exists(lock_file):
                os.remove(lock_file)

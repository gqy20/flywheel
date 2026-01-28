"""
Test for issue #801: Windows degraded mode behavior verification

This test verifies that the code behavior matches the documentation.
When pywin32 is not available on Windows, the module should:
1. Either implement a pure Python fallback (as documented)
2. Or update the documentation to reflect that locking is completely disabled
"""
import os
import sys
import tempfile
import warnings
from unittest import mock
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flywheel.storage import TodoStorage, _is_degraded_mode


class TestWindowsDegradedMode:
    """Test Windows degraded mode behavior (issue #801)."""

    def test_degraded_mode_detection_on_windows(self):
        """Test that degraded mode is correctly detected on Windows without pywin32."""
        # Mock Windows environment
        with mock.patch('os.name', 'nt'):
            with mock.patch('flywheel.storage.win32file', None):
                # Should detect degraded mode
                assert _is_degraded_mode() is True, \
                    "Windows without win32file should be in degraded mode"

    def test_degraded_mode_disables_locking_not_fallback(self):
        """
        Test issue #801: Verify actual behavior vs documentation.

        The documentation mentions "pure Python fallback" but actually
        file locking is completely disabled in degraded mode.
        This test documents the actual current behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock Windows environment without pywin32
            with mock.patch('os.name', 'nt'):
                # Force win32file to be None
                with mock.patch.dict('sys.modules', {'win32file': None}):
                    # Reimport to get the mocked version
                    import importlib
                    import flywheel.storage
                    importlib.reload(flywheel.storage)

                    # Create a TodoStorage instance
                    storage_path = os.path.join(tmpdir, 'test.json')
                    storage = flywheel.storage.TodoStorage(storage_path)

                    # Verify degraded mode is active
                    assert flywheel.storage._is_degraded_mode(), \
                        "Should be in degraded mode when win32file is None"

                    # Try to acquire a lock - this should not raise an error
                    # but should simply skip locking (actual behavior)
                    with open(storage_path, 'w') as f:
                        # This should not crash but should skip locking
                        storage._acquire_file_lock(f)

                    # The test verifies that no crash occurs in degraded mode
                    # This documents that locking is disabled, not using fallback

    def test_warning_message_accuracy(self):
        """
        Test issue #801: Verify warning message matches actual behavior.

        The current warning mentions "slower pure Python fallback" but
        the actual implementation disables locking entirely.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock Windows environment without pywin32
            with mock.patch('os.name', 'nt'):
                with mock.patch.dict('sys.modules',
                                     {'win32file': None,
                                      'win32security': None,
                                      'win32con': None,
                                      'win32api': None,
                                      'pywintypes': None}):
                    # Capture warnings
                    with warnings.catch_warnings(record=True) as w:
                        warnings.simplefilter("always")

                        # Reimport to trigger the warning
                        import importlib
                        import flywheel.storage
                        importlib.reload(flywheel.storage)

                        # Check if warning was issued
                        if len(w) > 0:
                            warning_messages = [str(warning.message) for warning in w]
                            # The warning should mention "pure Python fallback" if it exists
                            # or should clarify that locking is disabled
                            has_fallback_warning = any('fallback' in msg.lower() for msg in warning_messages)

                            # This test documents the discrepancy:
                            # If warning mentions fallback, there should be fallback code
                            # If no fallback code, warning should say "disabled" not "fallback"
                            if has_fallback_warning:
                                # TODO: Issue #801 - Either implement fallback or update warning
                                pytest.fail("Warning mentions fallback but no fallback exists (issue #801)")

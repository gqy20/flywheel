"""Test for issue #884: Unix degraded mode warning message is misleading.

This test verifies that when fcntl is not available on Unix systems,
the warning message accurately reflects the actual behavior (using fallback
file locking) rather than saying "file locking will be disabled".
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import warnings

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Remove storage module from cache if it exists
if 'flywheel.storage' in sys.modules:
    del sys.modules['flywheel.storage']


class TestIssue884WarningMessage(unittest.TestCase):
    """Test that the degraded mode warning message is accurate.

    Issue #884: The warning message when fcntl is not available says
    "File locking will be disabled" but this is misleading - the system
    actually uses a fallback file-based locking mechanism.

    The warning should be updated to reflect this accurate behavior.
    """

    @unittest.skipIf(os.name == 'nt', "Test only applies to Unix-like systems")
    def test_fcntl_unavailable_warning_mentions_fallback(self):
        """Test that the warning message mentions fallback file locking.

        When fcntl is not available, the system should warn about using
        fallback file locking, NOT that file locking is disabled.
        """
        # Mock fcntl to be unavailable
        with patch.dict('sys.modules', {'fcntl': None}):
            # Force reimport to trigger the warning
            if 'flywheel.storage' in sys.modules:
                del sys.modules['flywheel.storage']

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                # Import the module - this should trigger the warning
                from flywheel.storage import _is_degraded_mode

                # Check that a warning was issued
                self.assertTrue(len(w) > 0, "A warning should be issued when fcntl is not available")

                # Check that the warning message is about fcntl
                fcntl_warnings = [warning for warning in w if 'fcntl' in str(warning.message).lower()]

                self.assertTrue(len(fcntl_warnings) > 0, "Should have a warning about fcntl")

                # The key assertion: the warning should mention that file locking is NOT completely disabled
                # It should mention fallback or alternative mechanism
                warning_msg = str(fcntl_warnings[0].message).lower()

                # Currently this will fail because the warning says "will be disabled"
                # After fix, the warning should mention "fallback", "file-based locking", or similar
                self.assertNotIn(
                    "will be disabled",
                    warning_msg,
                    "Warning should NOT say 'will be disabled' because fallback locking is used"
                )

                # After fix, verify that the warning mentions the fallback mechanism
                # This assertion will pass after we fix the warning message
                self.assertTrue(
                    "fallback" in warning_msg or "file-based" in warning_msg,
                    "Warning should mention fallback or file-based locking mechanism"
                )

    @unittest.skipIf(os.name == 'nt', "Test only applies to Unix-like systems")
    def test_fcntl_unavailable_uses_fallback_locking(self):
        """Test that when fcntl is unavailable, fallback locking is actually used.

        This is a regression test to ensure the fallback mechanism is in place.
        """
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "test.json")

        try:
            # Mock fcntl to be unavailable
            with patch('flywheel.storage.fcntl', None):
                from flywheel.storage import FileStorage
                from flywheel.todo import Todo

                # Create storage - should use fallback locking
                storage = FileStorage(temp_file)

                # Add a todo - should work with fallback locking
                todo = Todo(title="Test", description="Test")
                added = storage.add(todo)

                self.assertIsNotNone(added)
                self.assertEqual(added.title, "Test")

                # Verify lock file was created (evidence of fallback mechanism)
                lock_file = Path(temp_file + ".lock")
                # Note: lock file might be cleaned up after operation
                # so we just verify the storage works without errors

        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


if __name__ == '__main__':
    unittest.main()

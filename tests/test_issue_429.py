"""Test for Issue #429 - Windows module import thread safety.

This test verifies that Windows security modules are imported at the module
level to prevent race conditions in multi-threaded environments.
"""

import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path


class TestWindowsModuleImportThreadSafety(unittest.TestCase):
    """Test Windows module imports are thread-safe (Issue #429)."""

    def test_windows_modules_imported_at_module_level(self):
        """Test that Windows security modules are imported at module level.

        This prevents race conditions in multi-threaded environments where
        __init__ checks could be bypassed or run concurrently with actual usage.
        """
        # Only test on Windows or when modules can be imported
        if os.name != 'nt':
            self.skipTest("Test only applies to Windows")

        # Import the storage module
        from flywheel import storage

        # Check if Windows modules are available at module level
        # This ensures imports happen once at module load, not per instance
        has_module_level_import = hasattr(storage, 'win32security') or \
                                  hasattr(storage, 'win32con') or \
                                  hasattr(storage, 'win32api') or \
                                  hasattr(storage, 'win32file') or \
                                  hasattr(storage, 'pywintypes')

        # At least one Windows module should be imported at module level
        # to ensure thread-safe initialization
        self.assertTrue(
            has_module_level_import,
            "Windows security modules should be imported at module level "
            "to prevent race conditions in multi-threaded environments"
        )

    def test_concurrent_storage_initialization_thread_safety(self):
        """Test that concurrent Storage initialization is thread-safe.

        This simulates the race condition scenario where multiple threads
        attempt to create Storage instances simultaneously.
        """
        if os.name != 'nt':
            self.skipTest("Test only applies to Windows")

        import threading
        from flywheel.storage import Storage
        import tempfile

        # Create temporary directory for test
        with tempfile.TemporaryDirectory() as tmpdir:
            results = []
            errors = []

            def create_storage():
                """Create a Storage instance in a thread."""
                try:
                    test_path = Path(tmpdir) / f"test_{threading.get_ident()}.json"
                    storage = Storage(str(test_path))
                    results.append(storage)
                except Exception as e:
                    errors.append(e)

            # Create multiple threads that attempt concurrent initialization
            threads = []
            num_threads = 10

            for _ in range(num_threads):
                thread = threading.Thread(target=create_storage)
                threads.append(thread)

            # Start all threads simultaneously
            for thread in threads:
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # All threads should succeed without errors
            self.assertEqual(
                len(errors), 0,
                f"Concurrent Storage initialization should succeed without errors. "
                f"Got {len(errors)} errors: {errors}"
            )

            # All threads should have created Storage instances
            self.assertEqual(
                len(results), num_threads,
                f"All threads should successfully create Storage instances"
            )

    def test_module_import_consistency_across_instances(self):
        """Test that module imports remain consistent across instances.

        This verifies that the module-level import check prevents
        inconsistencies between different Storage instances.
        """
        if os.name != 'nt':
            self.skipTest("Test only applies to Windows")

        from flywheel.storage import Storage
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create first instance
            storage1_path = Path(tmpdir) / "test1.json"
            storage1 = Storage(str(storage1_path))

            # Create second instance
            storage2_path = Path(tmpdir) / "test2.json"
            storage2 = Storage(str(storage2_path))

            # Both instances should coexist without errors
            self.assertIsNotNone(storage1)
            self.assertIsNotNone(storage2)

            # Module-level imports should be consistent
            # (no changes between instance creations)
            from flywheel import storage as storage_module
            first_import_state = hasattr(storage_module, 'win32security')

            # Create third instance
            storage3_path = Path(tmpdir) / "test3.json"
            storage3 = Storage(str(storage3_path))

            # Import state should remain consistent
            second_import_state = hasattr(storage_module, 'win32security')

            self.assertEqual(
                first_import_state, second_import_state,
                "Module import state should remain consistent across instances"
            )


if __name__ == '__main__':
    unittest.main()

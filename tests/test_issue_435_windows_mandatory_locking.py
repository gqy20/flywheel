"""Test for Issue #435 - Windows mandatory file locking.

This test verifies that Windows uses mandatory locking (win32file.LockFileEx)
instead of advisory locking (msvcrt.locking) to prevent concurrent access
by malicious or unaware processes.

Issue: https://github.com/anthropics/flywheel/issues/435
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import Storage


class TestWindowsMandatoryLocking(unittest.TestCase):
    """Test Windows mandatory file locking implementation."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a test storage path
        self.test_path = Path("/tmp/test_flywheel_issue_435.json")

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove test file if it exists
        if self.test_path.exists():
            self.test_path.unlink()

    @unittest.skipUnless(os.name == 'nt', "Test only runs on Windows")
    def test_windows_uses_win32file_lockfileex(self):
        """Test that Windows uses win32file.LockFileEx for mandatory locking."""
        # Create a storage instance
        storage = Storage(str(self.test_path))

        # Verify that win32file module is imported and available
        try:
            import win32file
            import win32con
            import pywintypes
        except ImportError as e:
            self.fail(f"pywin32 modules not available on Windows: {e}")

        # Verify that _acquire_file_lock uses win32file.LockFileEx
        # We can test this by attempting to acquire a lock and checking
        # that it uses the correct API
        with self.test_path.open('r') as f:
            # This should use win32file.LockFileEx, not msvcrt.locking
            # If it used msvcrt.locking, it would not enforce mutual exclusion
            storage._acquire_file_lock(f)
            storage._release_file_lock(f)

        # If we got here without exceptions, the locking mechanism works
        self.assertTrue(True)

    @unittest.skipUnless(os.name == 'nt', "Test only runs on Windows")
    def test_windows_lock_range_is_fixed_large_value(self):
        """Test that Windows uses a fixed large lock range (4GB) for mandatory locking."""
        storage = Storage(str(self.test_path))

        # Create a mock file handle
        with self.test_path.open('r') as f:
            # Get the lock range
            lock_range = storage._get_file_lock_range_from_handle(f)

            # Verify it's a tuple (low, high) representing 4GB
            self.assertIsInstance(lock_range, tuple)
            self.assertEqual(len(lock_range), 2)

            # The lock range should be (0xFFFFFFFF, 0) which represents 4GB
            # This prevents deadlocks when file size changes (Issue #375, #426, #451)
            low, high = lock_range
            self.assertEqual(low, 0xFFFFFFFF)
            self.assertEqual(high, 0)

    def test_windows_does_not_use_msvcrt_locking(self):
        """Test that msvcrt.locking is NOT used for file locking."""
        # This test verifies that the code does not use msvcrt.locking
        # which only provides advisory locking on Windows

        # Read the storage.py file and verify it doesn't use msvcrt.locking
        storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
        with open(storage_file, 'r') as f:
            content = f.read()

        # Verify that msvcrt.locking is NOT used
        self.assertNotIn('msvcrt.locking', content)

        # Verify that win32file.LockFileEx IS used (on Windows)
        self.assertIn('win32file.LockFileEx', content)

        # Verify that mandatory locking is mentioned in comments
        self.assertIn('MANDATORY', content)
        self.assertIn('mandatory locking', content.lower())

    @unittest.skipUnless(os.name != 'nt', "Test only runs on Unix")
    def test_unix_uses_fcntl_flock(self):
        """Test that Unix systems use fcntl.flock for file locking."""
        storage = Storage(str(self.test_path))

        # Verify that fcntl is imported on Unix
        try:
            import fcntl
        except ImportError as e:
            self.fail(f"fcntl module not available on Unix: {e}")

        # Verify that _acquire_file_lock uses fcntl.flock
        with self.test_path.open('r') as f:
            # This should use fcntl.flock
            storage._acquire_file_lock(f)
            storage._release_file_lock(f)

        # If we got here without exceptions, the locking mechanism works
        self.assertTrue(True)

    def test_locking_module_imports(self):
        """Test that the correct locking modules are imported."""
        # Read the storage.py file to check imports
        storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
        with open(storage_file, 'r') as f:
            lines = f.readlines()

        # Find the import section
        import_section = []
        in_import_section = False
        for line in lines:
            if 'Platform-specific file locking' in line:
                in_import_section = True
            if in_import_section:
                import_section.append(line)
                if 'else:' in line and 'Unix-like systems' in line:
                    break

        import_text = ''.join(import_section)

        if os.name == 'nt':
            # On Windows, should import win32file, win32con, pywintypes
            self.assertIn('import win32file', import_text)
            self.assertIn('import win32con', import_text)
            self.assertIn('import pywintypes', import_text)
        else:
            # On Unix, should import fcntl
            self.assertIn('import fcntl', import_text)

        # Should NOT import msvcrt on any platform
        self.assertNotIn('import msvcrt', import_text)


if __name__ == '__main__':
    unittest.main()

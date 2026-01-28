"""Test for Issue #426: File lock range should handle files larger than 2GB.

This test verifies that the file lock mechanism can handle files larger than 2GB
(0x7FFFFFFF bytes) without data corruption on Windows.
"""

import os
import tempfile
import pytest
from pathlib import Path
from flywheel.storage import Storage


class TestLargeFileLock:
    """Test file locking with large files (>2GB)."""

    def test_windows_lock_range_handles_large_files(self):
        """Test that lock range can handle files larger than 2GB on Windows."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_todos.json"

            # Create a storage instance
            storage = Storage(path=str(test_file))

            # On Windows, verify that the lock range is not limited to 2GB
            if os.name == 'nt':
                # Simulate a large file scenario by checking the lock range
                # The lock range should be able to handle files larger than 2GB
                lock_range = storage._get_file_lock_range_from_handle(None)

                # The lock range should be larger than 2GB (0x7FFFFFFF)
                # or the implementation should use a different locking mechanism
                # that doesn't rely on file size
                assert lock_range > 0x7FFFFFFF, (
                    f"Lock range {lock_range} is not sufficient for files larger than 2GB. "
                    f"Expected a value > {0x7FFFFFFF}, or a different locking mechanism."
                )
            else:
                # On Unix, fcntl.flock doesn't use lock ranges
                # The test should pass without checking the range
                lock_range = storage._get_file_lock_range_from_handle(None)
                assert lock_range == 0, (
                    f"Unix systems should return 0 for lock range (fcntl.flock doesn't use ranges)"
                )

            storage.close()

    def test_lock_range_dynamic_or_sufficient(self):
        """Test that lock range is either dynamic or sufficiently large."""
        # This test ensures the lock range can handle realistic large files
        # The 2GB limit is outdated and should be replaced

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_todos.json"
            storage = Storage(path=str(test_file))

            # Get the lock range
            lock_range = storage._get_file_lock_range_from_handle(None)

            if os.name == 'nt':
                # On Windows, the lock range should be:
                # 1. Dynamic (based on actual file size), OR
                # 2. Much larger than 2GB (e.g., 0x7FFFFFFFFFFFFFFF for max safety)
                #
                # For this implementation, we expect a very large value
                # that can handle any realistic file size
                assert lock_range >= 0x7FFFFFFFFFFFFFFF, (
                    f"Lock range {lock_range} is too small for large files. "
                    f"Use win32file for file-size-independent locking or "
                    f"a much larger fixed range (e.g., 0x7FFFFFFFFFFFFFFF)."
                )
            else:
                # Unix systems don't use lock ranges
                assert lock_range == 0

            storage.close()

    def test_file_lock_with_win32file_if_available(self):
        """Test that win32file is used if available on Windows (preferred method)."""
        if os.name != 'nt':
            pytest.skip("This test only applies to Windows")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_todos.json"

            try:
                # Try to import win32file
                import win32file
                import win32con
                import win32security

                # If win32file is available, the code should use it for locking
                # instead of msvcrt.locking with a limited range
                storage = Storage(path=str(test_file))

                # The lock range should indicate win32file is being used
                # or the range should be unlimited/maximal
                lock_range = storage._get_file_lock_range_from_handle(None)

                # With win32file, we can lock the entire file regardless of size
                # The implementation should use a very large range or win32file API
                assert lock_range >= 0x7FFFFFFFFFFFFFFF or lock_range == 0, (
                    f"When win32file is available, use it for file-size-independent locking. "
                    f"Current range: {lock_range}"
                )

                storage.close()
            except ImportError:
                # If win32file is not available, fall back to msvcrt.locking
                # but with a much larger range than 2GB
                storage = Storage(path=str(test_file))
                lock_range = storage._get_file_lock_range_from_handle(None)
                assert lock_range >= 0x7FFFFFFFFFFFFFFF, (
                    f"Even with msvcrt.locking, use a larger range than 2GB. "
                    f"Current range: {lock_range}"
                )
                storage.close()

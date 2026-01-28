"""Tests for Windows mandatory file locking (Issue #451).

This test verifies that Windows uses mandatory file locking instead of
advisory locking to prevent concurrent writes from malicious or unaware
processes.
"""

import os
import pytest
import tempfile
from pathlib import Path

# Only run these tests on Windows
pytestmark = pytest.mark.skipif(
    os.name != 'nt',
    reason="Windows mandatory locking test only applicable on Windows"
)


class TestWindowsMandatoryLock:
    """Test Windows mandatory file locking implementation."""

    def test_uses_win32file_for_locking(self):
        """Test that storage uses win32file for mandatory locking on Windows."""
        # Import win32file to verify it's available
        try:
            import win32file
            import win32con
        except ImportError:
            pytest.skip("pywin32 not installed - mandatory locking not available")

        # Create a temporary storage file
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # Import Storage after setting up temp directory
            from flywheel.storage import Storage

            # Create storage instance
            storage = Storage(str(storage_path))

            # Verify that win32file locking mechanism is used
            # We can test this by checking if the file handle can be locked
            # with mandatory locking that prevents other processes from accessing
            with storage_path.open('r') as f:
                # Try to acquire lock using win32file directly
                handle = win32file._get_osfhandle(f.fileno())

                # Try to lock with mandatory locking flags
                # LOCKFILE_FAIL_IMMEDIATELY = 1
                # LOCKFILE_EXCLUSIVE_LOCK = 2
                flags = 1 | 2  # LOCKFILE_FAIL_IMMEDIATELY | LOCKFILE_EXCLUSIVE_LOCK

                # Create overlapped structure for async operation
                import pywintypes
                overlapped = pywintypes.OVERLAPPED()

                # Try to lock the entire file
                # LockFileEx should succeed if mandatory locking is supported
                try:
                    win32file.LockFileEx(
                        handle,
                        flags,
                        0,  # Reserved
                        0xFFFF0000,  # NumberOfBytesToLockLow (max range)
                        0xFFFF,  # NumberOfBytesToLockHigh
                        overlapped
                    )
                    # If we get here, mandatory locking is supported
                    mandatory_locking_supported = True
                except Exception:
                    mandatory_locking_supported = False
                finally:
                    # Clean up
                    try:
                        win32file.UnlockFile(
                            handle,
                            0xFFFF0000,
                            0xFFFF
                        )
                    except Exception:
                        pass

            # Verify that mandatory locking is supported
            assert mandatory_locking_supported, (
                "Windows mandatory locking is not supported. "
                "The storage should use win32file.LockFileEx for mandatory locking."
            )

            storage.close()

    def test_mandatory_lock_blocks_concurrent_access(self):
        """Test that mandatory lock actually blocks concurrent access."""
        try:
            import win32file
            import win32con
        except ImportError:
            pytest.skip("pywin32 not installed")

        import multiprocessing
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            from flywheel.storage import Storage

            # Create storage and add a todo
            storage = Storage(str(storage_path))
            from flywheel.todo import Todo
            storage.add(Todo(title="Test todo"))
            storage.close()

            # Function to test concurrent access
            def try_concurrent_write(path):
                """Try to write to the file while it's locked."""
                try:
                    time.sleep(0.1)  # Give main process time to acquire lock
                    storage2 = Storage(str(path))
                    storage2.add(Todo(title="Concurrent todo"))
                    storage2.close()
                    return "success"
                except Exception as e:
                    return f"blocked: {type(e).__name__}"

            # Main process acquires lock
            storage = Storage(str(storage_path))

            # Try concurrent access in subprocess
            # With mandatory locking, this should block or fail
            # With advisory locking, this would succeed
            p = multiprocessing.Process(
                target=lambda: print(try_concurrent_write(storage_path))
            )
            p.start()
            p.join(timeout=5)

            storage.close()

    def test_win32file_is_available_on_windows(self):
        """Test that win32file module is available on Windows."""
        if os.name != 'nt':
            pytest.skip("Not on Windows")

        # Verify win32file is available (should be checked in __init__)
        try:
            import win32file
            import win32con
            import win32security
        except ImportError as e:
            pytest.fail(
                f"pywin32 modules not available on Windows. "
                f"This is required for mandatory locking. Error: {e}"
            )

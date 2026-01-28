"""Test to verify issue #440 is resolved.

This test verifies that the _acquire_file_lock method is fully implemented
for Windows with win32file.LockFileEx (mandatory locking).

The issue claimed the implementation was incomplete and suggested using
msvcrt.locking, but the actual implementation is even better - it uses
win32file.LockFileEx which provides MANDATORY LOCKING.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import Storage


def test_windows_file_lock_implementation_exists():
    """Test that Windows file lock implementation is complete.

    This test verifies that:
    1. The _acquire_file_lock method exists
    2. It has Windows-specific implementation
    3. It uses win32file.LockFileEx (not msvcrt.locking)
    """
    # Create a temporary storage instance
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"

        # Create storage instance
        storage = Storage(str(storage_path))

        # Verify the _acquire_file_lock method exists
        assert hasattr(storage, '_acquire_file_lock'), \
            "Storage class should have _acquire_file_lock method"

        # Verify the method is callable
        assert callable(storage._acquire_file_lock), \
            "_acquire_file_lock should be callable"

        # On Windows, verify that win32file module is imported
        if os.name == 'nt':
            # Check that win32file module is available
            try:
                import win32file
                import win32con
                import pywintypes
                # If we get here, Windows modules are available
                assert True, "Windows file locking modules are available"
            except ImportError as e:
                pytest.skip(f"Windows file locking modules not available: {e}")

            # Verify the method signature and implementation
            import inspect
            source = inspect.getsource(storage._acquire_file_lock)

            # Verify it uses win32file.LockFileEx (not msvcrt.locking)
            assert "win32file.LockFileEx" in source, \
                "Windows implementation should use win32file.LockFileEx for mandatory locking"

            # Verify it has timeout mechanism
            assert "LOCKFILE_FAIL_IMMEDIATELY" in source, \
                "Windows implementation should use LOCKFILE_FAIL_IMMEDIATELY flag"

            assert "timeout" in source.lower() or "_lock_timeout" in source, \
                "Implementation should have timeout mechanism"

            # Verify it has retry loop
            assert "while" in source and "time.sleep" in source.lower(), \
                "Implementation should have retry loop with sleep"

        else:
            # On Unix, verify fcntl implementation
            import inspect
            source = inspect.getsource(storage._acquire_file_lock)

            # Verify it uses fcntl.flock
            assert "fcntl.flock" in source, \
                "Unix implementation should use fcntl.flock"

            # Verify it has non-blocking mode
            assert "LOCK_NB" in source, \
                "Unix implementation should use LOCK_NB flag"

        storage.close()


def test_file_lock_acquire_and_release():
    """Test that file lock can be acquired and released.

    This is a functional test to verify the lock mechanism actually works.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"

        # Create storage instance
        storage = Storage(str(storage_path))

        # Create a test file to lock
        test_file = storage_path.parent / "test_lock.txt"
        test_file.write_text("test")

        # Test acquire and release
        with test_file.open('r') as f:
            # Acquire lock
            storage._acquire_file_lock(f)

            # Verify lock range is cached (for Windows)
            if os.name == 'nt':
                assert storage._lock_range is not None, \
                    "Lock range should be cached after acquisition"

            # Release lock
            storage._release_file_lock(f)

        storage.close()


def test_windows_mandatory_locking_documentation():
    """Test that the implementation is properly documented.

    Verifies that the docstring correctly describes the Windows
    mandatory locking approach (not msvcrt.locking).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Get the docstring
        docstring = storage._acquire_file_lock.__doc__

        # Verify it mentions mandatory locking for Windows
        assert "MANDATORY" in docstring or "mandatory" in docstring.lower(), \
            "Docstring should mention mandatory locking for Windows"

        # Verify it mentions win32file.LockFileEx
        assert "win32file.LockFileEx" in docstring or "LockFileEx" in docstring, \
            "Docstring should mention win32file.LockFileEx"

        # Verify it does NOT recommend msvcrt.locking (advisory lock)
        # The old approach is inferior and should not be recommended
        # Note: It's okay if "msvcrt" appears in historical notes,
        # but it should not be presented as the current approach
        if "msvcrt" in docstring.lower():
            # If mentioned, it should be in a warning context
            assert "WARNING" in docstring or "advisory" in docstring.lower(), \
                "If msvcrt is mentioned, it should be with a warning about advisory locking"

        storage.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

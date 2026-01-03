"""Test file lock functionality (Issue #430).

This test verifies that the _acquire_file_lock method is fully implemented
and works correctly on both Windows and Unix-like systems.
"""

import os
import tempfile
import pytest
from pathlib import Path

from flywheel.storage import Storage


class TestFileLockImplementation:
    """Test that file locking is correctly implemented."""

    def test_file_lock_method_exists(self):
        """Test that _acquire_file_lock method exists and is callable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(path=os.path.join(tmpdir, "todos.json"))
            assert hasattr(storage, '_acquire_file_lock')
            assert callable(storage._acquire_file_lock)

    def test_file_lock_has_timeout(self):
        """Test that file lock timeout is configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(path=os.path.join(tmpdir, "todos.json"))
            assert hasattr(storage, '_lock_timeout')
            assert storage._lock_timeout > 0
            assert storage._lock_timeout == 30.0  # Default timeout

    def test_file_lock_has_retry_interval(self):
        """Test that file lock retry interval is configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(path=os.path.join(tmpdir, "todos.json"))
            assert hasattr(storage, '_lock_retry_interval')
            assert storage._lock_retry_interval > 0
            assert storage._lock_retry_interval == 0.1  # Default retry interval

    def test_acquire_and_release_lock(self):
        """Test that file lock can be acquired and released."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "todos.json")
            storage = Storage(path=storage_path)

            # Create a test file
            test_file = Path(storage_path)
            test_file.write_text("{}")

            # Acquire lock
            with test_file.open('r') as f:
                storage._acquire_file_lock(f)
                # Lock should be held now
                # Release lock
                storage._release_file_lock(f)

    def test_lock_range_is_cached(self):
        """Test that lock range is cached after acquisition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "todos.json")
            storage = Storage(path=storage_path)

            # Create a test file
            test_file = Path(storage_path)
            test_file.write_text("{}")

            # Initially, lock range should be 0 (not cached)
            assert storage._lock_range == 0

            # Acquire lock
            with test_file.open('r') as f:
                storage._acquire_file_lock(f)
                # Lock range should be cached
                if os.name == 'nt':  # Windows
                    assert isinstance(storage._lock_range, tuple)
                    assert len(storage._lock_range) == 2
                    assert storage._lock_range == (0, 1)  # 4GB lock range
                else:  # Unix
                    assert storage._lock_range == 0
                # Release lock
                storage._release_file_lock(f)

    def test_get_file_lock_range_from_handle(self):
        """Test that _get_file_lock_range_from_handle returns correct values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "todos.json")
            storage = Storage(path=storage_path)

            # Create a test file
            test_file = Path(storage_path)
            test_file.write_text("{}")

            with test_file.open('r') as f:
                lock_range = storage._get_file_lock_range_from_handle(f)

                if os.name == 'nt':  # Windows
                    assert isinstance(lock_range, tuple)
                    assert len(lock_range) == 2
                    assert lock_range == (0, 1)  # 4GB lock range
                else:  # Unix
                    assert lock_range == 0

    def test_windows_implementation_complete(self):
        """Test that Windows file lock implementation is complete."""
        if os.name != 'nt':
            pytest.skip("Windows-only test")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "todos.json")
            storage = Storage(path=storage_path)

            # Create a test file
            test_file = Path(storage_path)
            test_file.write_text("{}")

            # Verify Windows modules can be imported
            try:
                import pywintypes
                import win32file
                import win32con
            except ImportError:
                pytest.fail("pywin32 modules not available on Windows")

            # Acquire lock
            with test_file.open('r') as f:
                # This should work without errors
                storage._acquire_file_lock(f)
                storage._release_file_lock(f)

    def test_unix_implementation_complete(self):
        """Test that Unix file lock implementation is complete."""
        if os.name == 'nt':
            pytest.skip("Unix-only test")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "todos.json")
            storage = Storage(path=storage_path)

            # Create a test file
            test_file = Path(storage_path)
            test_file.write_text("{}")

            # Verify fcntl is available
            try:
                import fcntl
            except ImportError:
                pytest.fail("fcntl module not available on Unix")

            # Acquire lock
            with test_file.open('r') as f:
                # This should work without errors
                storage._acquire_file_lock(f)
                storage._release_file_lock(f)

    def test_lock_timeout_raises_runtime_error(self):
        """Test that lock timeout raises RuntimeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "todos.json")
            storage = Storage(path=storage_path)

            # Set a very short timeout for testing
            original_timeout = storage._lock_timeout
            storage._lock_timeout = 0.1  # 100ms timeout

            try:
                # Create a test file
                test_file = Path(storage_path)
                test_file.write_text("{}")

                # Acquire first lock
                with test_file.open('r') as f1:
                    storage._acquire_file_lock(f1)

                    # Try to acquire second lock (should timeout)
                    # Note: This test is platform-dependent and may not always work
                    # as expected on all systems
                    try:
                        with test_file.open('r') as f2:
                            # This should timeout
                            with pytest.raises(RuntimeError, match="timed out"):
                                storage._acquire_file_lock(f2)
                    finally:
                        storage._release_file_lock(f1)
            finally:
                # Restore original timeout
                storage._lock_timeout = original_timeout

"""Test file lock timeout and retry mechanism (Issue #777).

This test verifies that file lock acquisition supports configurable timeout
and retry mechanism to prevent indefinite hangs in multi-process environments.
"""

import os
import pytest
import tempfile
import time
import multiprocessing
import json
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestFileLockTimeoutConfiguration:
    """Test file lock timeout configuration."""

    def test_default_timeout_exists(self):
        """Test that default file lock timeout is configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Verify default timeout exists (should be 30.0 seconds)
            assert hasattr(storage, '_lock_timeout')
            assert storage._lock_timeout > 0
            assert storage._lock_timeout == 30.0

    def test_default_retry_interval_exists(self):
        """Test that default retry interval is configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # Verify default retry interval exists (should be 0.1 seconds)
            assert hasattr(storage, '_lock_retry_interval')
            assert storage._lock_retry_interval > 0
            assert storage._lock_retry_interval == 0.1

    def test_custom_timeout_parameter(self):
        """Test that custom timeout can be configured via parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # This test will fail initially, as timeout parameter is not yet supported
            # After implementation, this should create a storage with custom timeout
            storage = Storage(str(storage_path), lock_timeout=5.0)

            # Verify custom timeout is applied
            assert storage._lock_timeout == 5.0

    def test_custom_retry_interval_parameter(self):
        """Test that custom retry interval can be configured via parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # This test will fail initially, as retry_interval parameter is not yet supported
            # After implementation, this should create a storage with custom retry interval
            storage = Storage(str(storage_path), lock_retry_interval=0.05)

            # Verify custom retry interval is applied
            assert storage._lock_retry_interval == 0.05

    def test_invalid_timeout_raises_error(self):
        """Test that invalid timeout values raise appropriate errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # Negative timeout should raise ValueError
            with pytest.raises(ValueError, match="lock_timeout must be positive"):
                Storage(str(storage_path), lock_timeout=-1.0)

            # Zero timeout should raise ValueError
            with pytest.raises(ValueError, match="lock_timeout must be positive"):
                Storage(str(storage_path), lock_timeout=0.0)

    def test_invalid_retry_interval_raises_error(self):
        """Test that invalid retry interval values raise appropriate errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"

            # Negative retry interval should raise ValueError
            with pytest.raises(ValueError, match="lock_retry_interval must be positive"):
                Storage(str(storage_path), lock_retry_interval=-0.1)

            # Zero retry interval should raise ValueError
            with pytest.raises(ValueError, match="lock_retry_interval must be positive"):
                Storage(str(storage_path), lock_retry_interval=0.0)


def hold_lock_and_timeout(temp_file_path, duration):
    """Helper function to hold a file lock for specified duration.

    This function is used in multi-process tests to simulate a competing
    process holding the lock for an extended period.

    Args:
        temp_file_path: Path to the file to lock.
        duration: Time to hold the lock in seconds.
    """
    if os.name == 'nt':
        # Windows: Try to use pywin32 if available
        try:
            import win32file
            import win32con
            import pywintypes

            with open(temp_file_path, 'w') as f:
                f.write(json.dumps({"test": "data"}))
                win_handle = win32file._get_osfhandle(f.fileno())
                overlapped = pywintypes.OVERLAPPED()

                # Acquire exclusive lock
                win32file.LockFileEx(
                    win_handle,
                    win32con.LOCKFILE_EXCLUSIVE_LOCK,
                    0,
                    0,  # Lock length low
                    1,  # Lock length high (4GB)
                    overlapped
                )

                # Hold the lock for the specified duration
                time.sleep(duration)

        except ImportError:
            # pywin32 not available, skip this test
            pass
    else:
        # Unix: Use fcntl
        import fcntl

        with open(temp_file_path, 'w') as f:
            f.write(json.dumps({"test": "data"}))
            # Acquire exclusive lock
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            # Hold the lock for the specified duration
            time.sleep(duration)


class TestFileLockTimeoutBehavior:
    """Test file lock timeout behavior with competing processes."""

    @pytest.mark.skipif(
        os.name == 'nt' and True,  # Skip on Windows initially
        reason="Timeout test requires separate process coordination"
    )
    def test_lock_timeout_with_competing_process(self):
        """Test that lock acquisition times out when competing process holds lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage_path_str = str(storage_path)

            # Create a file first
            with open(storage_path_str, 'w') as f:
                json.dump([], f)

            # Start a process that will hold the lock for 2 seconds
            holder = multiprocessing.Process(
                target=hold_lock_and_timeout,
                args=(storage_path_str, 2.0)
            )
            holder.start()

            # Wait a bit for the holder to acquire the lock
            time.sleep(0.2)

            # Try to create storage with a short timeout
            # This should timeout after 0.5 seconds
            start_time = time.time()
            try:
                storage = Storage(storage_path_str, lock_timeout=0.5)
                # If we get here, the lock was acquired (holder released)
                elapsed = time.time() - start_time
                assert elapsed >= 0.4  # Should have waited at least 0.4 seconds
            except RuntimeError as e:
                # Expected: timeout error
                elapsed = time.time() - start_time
                assert "timeout" in str(e).lower()
                assert elapsed >= 0.4  # Should have waited at least timeout duration
            finally:
                holder.join(timeout=5.0)
                if holder.is_alive():
                    holder.terminate()

    def test_quick_lock_acquisition_with_no_contention(self):
        """Test that lock acquisition is quick when there's no contention."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_todos.json"
            storage = Storage(str(storage_path))

            # This should complete very quickly (no lock contention)
            start_time = time.time()
            todo = Todo(title="Quick lock test")
            storage.add(todo)
            elapsed = time.time() - start_time

            # Should complete in under 1 second (no contention)
            assert elapsed < 1.0
            assert storage.get(todo.id) is not None

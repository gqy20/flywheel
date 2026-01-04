"""Test file lock retry mechanism (Issue #653).

This test verifies that file lock acquisition includes a retry mechanism
to handle temporary file locks held by other processes.
"""

import os
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from flywheel.storage import Storage


@pytest.mark.skipif(
    os.name == 'nt',
    reason="This test is for Unix-like systems (fcntl.flock)"
)
class TestUnixLockRetryMechanism:
    """Test file lock retry mechanism on Unix-like systems."""

    def test_lock_retry_attempts_exist(self):
        """Test that lock acquisition uses retry mechanism."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_storage.json"
            storage = Storage(str(storage_path))

            # Verify that retry interval is configured
            assert hasattr(storage, '_lock_retry_interval')
            assert storage._lock_retry_interval > 0
            assert storage._lock_retry_interval < 1.0  # Should be reasonable (< 1s)

            # Verify that timeout is configured
            assert hasattr(storage, '_lock_timeout')
            assert storage._lock_timeout > 0

    def test_lock_retries_on_temporary_contention(self):
        """Test that lock acquisition retries when lock is temporarily held."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_storage.json"
            storage = Storage(str(storage_path))

            # Track how many times flock is called
            original_flock = __import__('fcntl').flock.flock
            call_count = [0]
            should_fail_count = [2]  # Fail first 2 attempts, succeed on 3rd

            def mock_flock(fd, operation):
                call_count[0] += 1
                if call_count[0] <= should_fail_count[0]:
                    # Simulate lock held by another process
                    import errno
                    raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
                # After failures, succeed
                return original_flock(fd, operation)

            with patch('fcntl.flock', side_effect=mock_flock):
                # Try to perform a file operation
                from flywheel.todo import Todo
                todo = Todo(title="Retry test")

                # This should succeed after retries
                storage.add(todo)

                # Verify that multiple attempts were made
                assert call_count[0] > 1, "Lock should have been attempted multiple times"
                assert call_count[0] == should_fail_count[0] + 1

    def test_lock_respects_timeout(self):
        """Test that lock acquisition respects timeout configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_storage.json"
            storage = Storage(str(storage_path))

            # Mock flock to always fail (lock always held)
            import errno
            def mock_flock_always_fail(fd, operation):
                raise IOError(errno.EAGAIN, "Resource temporarily unavailable")

            with patch('fcntl.flock', side_effect=mock_flock_always_fail):
                # Set a short timeout for testing
                storage._lock_timeout = 0.5
                storage._lock_retry_interval = 0.1

                start_time = time.time()

                # Try to perform a file operation - should timeout
                from flywheel.todo import Todo
                todo = Todo(title="Timeout test")

                with pytest.raises(RuntimeError, match="timed out"):
                    storage.add(todo)

                elapsed = time.time() - start_time

                # Should have waited approximately the timeout duration
                # Allow some margin for test execution overhead
                assert 0.4 <= elapsed <= 1.0, f"Timeout should be ~0.5s, got {elapsed:.2f}s"


@pytest.mark.skipif(
    os.name != 'nt',
    reason="This test is for Windows systems (win32file)"
)
class TestWindowsLockRetryMechanism:
    """Test file lock retry mechanism on Windows."""

    def test_lock_retry_attempts_exist(self):
        """Test that lock acquisition uses retry mechanism."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_storage.json"
            storage = Storage(str(storage_path))

            # Verify that retry interval is configured
            assert hasattr(storage, '_lock_retry_interval')
            assert storage._lock_retry_interval > 0
            assert storage._lock_retry_interval < 1.0

            # Verify that timeout is configured
            assert hasattr(storage, '_lock_timeout')
            assert storage._lock_timeout > 0

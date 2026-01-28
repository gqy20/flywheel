"""Test retry mechanism for transient failures (Issue #897).

This test verifies that:
1. A retry decorator exists for handling transient failures
2. Storage methods use retry logic for transient errors
3. Retry uses exponential backoff
4. Retry eventually fails after max attempts
"""

import errno
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


class TestRetryMechanism:
    """Test suite for retry mechanism on storage operations."""

    def test_retry_decorator_exists(self):
        """Verify that the retry_transient_errors decorator exists."""
        try:
            from flywheel.storage import retry_transient_errors
            assert callable(retry_transient_errors), "retry_transient_errors should be callable"
        except ImportError:
            pytest.fail("retry_transient_errors decorator should exist in flywheel.storage")

    def test_retry_on_transient_ioerror(self):
        """Test that storage methods retry on transient IOError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create storage with initial data
            storage = FileStorage(str(storage_path))
            todo1 = Todo(title="Initial todo", description="Initial description")
            storage.add(todo1)
            storage.close()

            # Create a new storage instance that will fail on first attempt
            storage2 = FileStorage(str(storage_path))

            # Mock the save method to fail once then succeed
            original_save = storage2._save_with_todos_sync
            attempt_count = [0]

            def flaky_save(todos):
                attempt_count[0] += 1
                if attempt_count[0] == 1:
                    # First attempt fails with a transient error
                    raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
                else:
                    # Second attempt succeeds
                    return original_save(todos)

            storage2._save_with_todos_sync = flaky_save

            # This should succeed after retry
            todo2 = Todo(title="Retry todo", description="Should succeed on retry")
            result = storage2.add(todo2)

            assert result is not None, "Add should succeed after retry"
            assert attempt_count[0] == 2, "Should have retried once"
            storage2.close()

    def test_retry_with_exponential_backoff(self):
        """Test that retry uses exponential backoff."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = FileStorage(str(storage_path))

            # Mock the save method to fail multiple times
            original_save = storage._save_with_todos_sync
            attempt_count = [0]
            timestamps = []

            def flaky_save(todos):
                attempt_count[0] += 1
                timestamps.append(time.time())
                if attempt_count[0] <= 2:
                    # First two attempts fail
                    raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
                else:
                    # Third attempt succeeds
                    return original_save(todos)

            storage._save_with_todos_sync = flaky_save

            # This should succeed after retries
            todo = Todo(title="Backoff test", description="Test exponential backoff")
            start = time.time()
            result = storage.add(todo)
            elapsed = time.time() - start

            assert result is not None, "Add should succeed after retries"
            assert attempt_count[0] == 3, "Should have retried twice"

            # Verify exponential backoff: delays should increase
            if len(timestamps) >= 3:
                delay1 = timestamps[1] - timestamps[0]
                delay2 = timestamps[2] - timestamps[1]
                # Second delay should be longer (exponential backoff)
                # Allow some tolerance for execution time
                assert delay2 > delay1 * 0.8, "Should use exponential backoff"

            storage.close()

    def test_retry_fails_after_max_attempts(self):
        """Test that retry eventually fails after max attempts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = FileStorage(str(storage_path))

            # Mock the save method to always fail
            attempt_count = [0]

            def always_failing_save(todos):
                attempt_count[0] += 1
                raise IOError(errno.EAGAIN, "Resource temporarily unavailable")

            storage._save_with_todos_sync = always_failing_save

            # This should fail after max retries
            todo = Todo(title="Fail test", description="Should fail after max retries")
            with pytest.raises(IOError):
                storage.add(todo)

            # Should have attempted multiple times (default max retries)
            assert attempt_count[0] > 1, "Should have attempted multiple retries"
            storage.close()

    def test_retry_on_permission_denied(self):
        """Test that storage methods retry on permission denied errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = FileStorage(str(storage_path))

            # Mock the save method to fail with permission denied then succeed
            original_save = storage._save_with_todos_sync
            attempt_count = [0]

            def flaky_save(todos):
                attempt_count[0] += 1
                if attempt_count[0] == 1:
                    # First attempt fails with permission denied
                    raise IOError(errno.EACCES, "Permission denied")
                else:
                    # Second attempt succeeds
                    return original_save(todos)

            storage._save_with_todos_sync = flaky_save

            # This should succeed after retry
            todo = Todo(title="Permission test", description="Should retry on permission denied")
            result = storage.add(todo)

            assert result is not None, "Add should succeed after retry"
            assert attempt_count[0] == 2, "Should have retried once"
            storage.close()

    def test_no_retry_on_permanent_errors(self):
        """Test that permanent errors are not retried."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = FileStorage(str(storage_path))

            # Mock the save method to fail with a permanent error
            attempt_count = [0]

            def failing_save(todos):
                attempt_count[0] += 1
                raise IOError(errno.ENOSPC, "No space left on device")

            storage._save_with_todos_sync = failing_save

            # This should fail immediately without retry
            todo = Todo(title="Permanent error", description="Should not retry")
            with pytest.raises(IOError):
                storage.add(todo)

            # Should only attempt once (no retry for permanent errors)
            assert attempt_count[0] == 1, "Should not retry on permanent errors"
            storage.close()

    def test_retry_on_update_operation(self):
        """Test that update operations also use retry logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = FileStorage(str(storage_path))

            # Add initial todo
            todo = Todo(title="Update test", description="Initial description")
            added = storage.add(todo)

            # Mock the save method to fail once then succeed
            original_save = storage._save_with_todos_sync
            attempt_count = [0]

            def flaky_save(todos):
                attempt_count[0] += 1
                if attempt_count[0] == 1:
                    raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
                else:
                    return original_save(todos)

            storage._save_with_todos_sync = flaky_save

            # Update should succeed after retry
            added.title = "Updated title"
            result = storage.update(added)

            assert result is not None, "Update should succeed after retry"
            assert attempt_count[0] == 2, "Should have retried once"
            storage.close()

    def test_retry_on_delete_operation(self):
        """Test that delete operations also use retry logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = FileStorage(str(storage_path))

            # Add initial todo
            todo = Todo(title="Delete test", description="Will be deleted")
            added = storage.add(todo)

            # Mock the save method to fail once then succeed
            original_save = storage._save_with_todos_sync
            attempt_count = [0]

            def flaky_save(todos):
                attempt_count[0] += 1
                if attempt_count[0] == 1:
                    raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
                else:
                    return original_save(todos)

            storage._save_with_todos_sync = flaky_save

            # Delete should succeed after retry
            result = storage.delete(added.id)

            assert result is True, "Delete should succeed after retry"
            assert attempt_count[0] == 2, "Should have retried once"
            storage.close()

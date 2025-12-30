"""Test for Issue #100 - Handle OSError in os.write loop.

This test verifies that the Storage class can handle OSError exceptions
that may occur during os.write() operations, particularly when interrupted
by signals (EINTR).
"""

import errno
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_os_write_handles_eintr():
    """Test that os.write EINTR errors are handled gracefully.

    When os.write is interrupted by a signal (errno.EINTR), it should
    automatically retry rather than failing.
    """
    # Create a temporary storage
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo to trigger a save operation
        todo = Todo(title="Test todo")
        storage.add(todo)

        # Mock os.write to simulate EINTR on first call, then succeed
        original_write = os.write
        call_count = [0]

        def mock_write(fd, data):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: simulate signal interruption
                raise OSError(errno.EINTR, "Interrupted system call")
            else:
                # Second call: succeed
                return original_write(fd, data)

        with patch("os.write", side_effect=mock_write):
            # This should succeed despite EINTR error
            # The write should be automatically retried
            todo2 = Todo(title="Another todo")
            # This should not raise an exception
            result = storage.add(todo2)

        assert result is not None
        assert result.title == "Another todo"

        # Verify the file was written correctly
        todos = storage.list()
        assert len(todos) == 2


def test_os_write_handles_other_oserror():
    """Test that other OSError types are not silently retried.

    Errors like ENOSPC (disk full) should not be retried indefinitely.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo to trigger initial save
        todo = Todo(title="Test todo")
        storage.add(todo)

        # Mock os.write to simulate ENOSPC (disk full)
        def mock_write_enospc(fd, data):
            raise OSError(errno.ENOSPC, "No space left on device")

        with patch("os.write", side_effect=mock_write_enospc):
            # This should raise an exception
            with pytest.raises(OSError) as exc_info:
                todo2 = Todo(title="Another todo")
                storage.add(todo2)

            # Verify it's the correct error type
            assert exc_info.value.errno == errno.ENOSPC


def test_os_write_partial_write_handling():
    """Test that partial writes are handled correctly.

    This verifies the existing behavior where os.write returns fewer
    bytes than requested, and the loop continues writing.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = Todo(title="Test todo")
        storage.add(todo)

        # Mock os.write to simulate partial writes
        original_write = os.write
        call_count = [0]

        def mock_write_partial(fd, data):
            call_count[0] += 1
            # Write only 10 bytes at a time
            bytes_to_write = min(10, len(data))
            result = original_write(fd, data[:bytes_to_write])
            return result

        with patch("os.write", side_effect=mock_write_partial):
            # This should succeed despite partial writes
            todo2 = Todo(title="Another todo with longer title")
            result = storage.add(todo2)

        assert result is not None
        assert result.title == "Another todo with longer title"

        # Verify the file was written correctly
        todos = storage.list()
        assert len(todos) == 2


def test_os_write_zero_bytes_raises_error():
    """Test that os.write returning 0 bytes raises an error.

    This indicates a serious issue like disk full.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo
        todo = Todo(title="Test todo")
        storage.add(todo)

        # Mock os.write to return 0 bytes
        with patch("os.write", return_value=0):
            # This should raise an OSError
            with pytest.raises(OSError, match="Write returned 0 bytes"):
                todo2 = Todo(title="Another todo")
                storage.add(todo2)

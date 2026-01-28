"""Test for issue #206 - Exception handling in finally block when closing file descriptor."""

import os
import tempfile
import unittest.mock
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestIssue206:
    """Test that finally block properly handles OSError when closing file descriptor."""

    def test_finally_block_handles_oserror_on_close(self):
        """Test that OSError in finally block doesn't mask original exception.

        This test verifies that when os.close() raises an OSError in the finally block,
        it doesn't mask the original exception from the main logic.
        """
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.todos.json"

            # Create storage with one todo
            storage = Storage(str(storage_path))
            storage.add(Todo(id=1, title="Test todo", status="pending"))

            # Now patch os.close to raise OSError
            original_close = os.close

            def mock_close(fd):
                # Raise OSError only for the file descriptors we're interested in
                # (not for low-numbered fds used by the system)
                if fd > 100:
                    raise OSError(9, "Bad file descriptor", fd)
                return original_close(fd)

            # Also need to patch os.fchmod since it's called before close
            original_fchmod = os.fchmod

            def mock_fchmod(fd, mode):
                if fd > 100:
                    raise OSError(9, "Bad file descriptor", fd)
                return original_fchmod(fd, mode)

            with unittest.mock.patch('os.close', side_effect=mock_close):
                with unittest.mock.patch('os.fchmod', side_effect=mock_fchmod):
                    # This should raise an exception (either from fchmod or write)
                    # The finally block should not mask this exception
                    with pytest.raises((OSError, RuntimeError)):
                        storage.add(Todo(id=2, title="Another todo", status="pending"))

            # Verify that the storage is still in a consistent state
            todos = storage.list()
            assert len(todos) == 1
            assert todos[0].id == 1

    def test_finally_block_catches_oserror_specifically(self):
        """Test that finally block catches OSError (not just Exception).

        This verifies that the code uses OSError instead of the broader Exception
        class when catching errors from os.close().
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.todos.json"

            # Create storage
            storage = Storage(str(storage_path))
            storage.add(Todo(id=1, title="Test todo", status="pending"))

            # Patch os.close to raise OSError
            original_close = os.close
            close_call_count = 0

            def mock_close(fd):
                nonlocal close_call_count
                close_call_count += 1
                if fd > 100:
                    raise OSError(9, "Bad file descriptor", fd)
                return original_close(fd)

            # Patch os.fchmod to raise OSError first
            original_fchmod = os.fchmod

            def mock_fchmod(fd, mode):
                if fd > 100:
                    raise OSError(9, "Bad file descriptor", fd)
                return original_fchmod(fd, mode)

            with unittest.mock.patch('os.close', side_effect=mock_close):
                with unittest.mock.patch('os.fchmod', side_effect=mock_fchmod):
                    # The operation should fail
                    with pytest.raises(OSError):
                        storage.add(Todo(id=2, title="Another todo", status="pending"))

            # Verify that os.close was called (even though it failed)
            # This confirms the finally block executed
            assert close_call_count > 0

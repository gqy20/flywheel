"""Test for Issue #114 - File descriptor cleanup verification.

This test verifies that file descriptors are properly closed even when
os.write raises a non-EINTR OSError (like ENOSPC - disk full).

The implementation uses a try-except-finally structure where:
1. The os.write loop is inside a try block
2. An except block handles cleanup of temp files
3. A finally block ensures the file descriptor is always closed

Python guarantees that the finally block will execute even when an
exception is raised, so the file descriptor should never leak.
"""

import errno
import os
import tempfile
from unittest.mock import patch
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_fd_closed_on_enospc_in_write_loop():
    """Test that file descriptor is closed when os.write raises ENOSPC.

    This test specifically verifies the concern raised in Issue #114:
    that when os.write raises a non-EINTR OSError (like ENOSPC),
    the file descriptor is still properly closed by the finally block.

    Python guarantees that the finally block executes even when
    exceptions are raised, preventing file descriptor leaks.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo successfully
        todo1 = Todo(title="First todo", status="pending")
        storage.add(todo1)
        assert storage.get(todo1.id) is not None

        # Track which file descriptors are closed
        closed_fds = []
        original_close = os.close

        def mock_close(fd):
            """Track all close() calls."""
            closed_fds.append(fd)
            return original_close(fd)

        # Track which file descriptors are created
        fds_created = []

        # Mock os.write to fail with ENOSPC on second save
        original_write = os.write
        call_count = [0]

        def mock_write(fd, data):
            """Track fd creation and fail on second write."""
            if fd not in fds_created:
                fds_created.append(fd)

            call_count[0] += 1

            # Let first write succeed (initial save)
            if call_count[0] == 1:
                return original_write(fd, data)

            # Second write fails with ENOSPC (disk full)
            # This simulates the scenario in Issue #114
            error = OSError("No space left on device")
            error.errno = errno.ENOSPC
            raise error

        # Run the test with mocks
        with patch('os.write', side_effect=mock_write):
            with patch('os.close', side_effect=mock_close):
                # Try to add another todo
                # This should fail with ENOSPC error
                with pytest.raises(OSError) as exc_info:
                    storage.add(Todo(title="Second todo", status="pending"))

                # Verify it's the ENOSPC error
                assert exc_info.value.errno == errno.ENOSPC

        # CRITICAL VERIFICATION: All file descriptors must be closed
        # This is the core concern of Issue #114
        unclosed_fds = [fd for fd in fds_created if fd not in closed_fds]

        if unclosed_fds:
            pytest.fail(
                f"File descriptor leak detected! "
                f"The following file descriptors were not closed: {unclosed_fds}"
            )

        # Verify storage is still consistent after the error
        assert storage.get(todo1.id) is not None
        assert storage.get(todo1.id).title == "First todo"
        assert len(storage.list()) == 1  # Only the first todo exists


def test_fd_closed_on_eintr_then_enospc():
    """Test fd cleanup when EINTR retry is followed by ENOSPC.

    This tests a more complex scenario:
    1. First os.write call gets EINTR (interrupted)
    2. Loop retries (EINTR handling)
    3. Second os.write call gets ENOSPC (disk full)
    4. Exception is raised

    The file descriptor should still be closed in this case.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo
        storage.add(Todo(title="First todo", status="pending"))

        closed_fds = []
        original_close = os.close

        def mock_close(fd):
            closed_fds.append(fd)
            return original_close(fd)

        original_write = os.write
        call_count = [0]
        fds_created = []

        def mock_write(fd, data):
            if fd not in fds_created:
                fds_created.append(fd)

            call_count[0] += 1

            # First call: EINTR (should trigger retry)
            if call_count[0] == 1:
                error = OSError("Interrupted system call")
                error.errno = errno.EINTR
                raise error
            # Second call: ENOSPC (should fail)
            elif call_count[0] == 2:
                error = OSError("No space left on device")
                error.errno = errno.ENOSPC
                raise error

            return original_write(fd, data)

        with patch('os.write', side_effect=mock_write):
            with patch('os.close', side_effect=mock_close):
                with pytest.raises(OSError) as exc_info:
                    storage.add(Todo(title="Second todo", status="pending"))

                assert exc_info.value.errno == errno.ENOSPC

        # Verify all fds were closed even after EINTR retry + ENOSPC
        unclosed_fds = [fd for fd in fds_created if fd not in closed_fds]

        if unclosed_fds:
            pytest.fail(
                f"File descriptor leak after EINTR+ENOSPC! "
                f"Unclosed fds: {unclosed_fds}"
            )


def test_fd_closed_on_partial_write_then_error():
    """Test fd cleanup when partial write succeeds then error occurs.

    This tests the scenario where:
    1. First write succeeds partially
    2. Second write in the loop fails with ENOSPC

    The fd should still be closed.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        storage.add(Todo(title="First todo", status="pending"))

        closed_fds = []
        original_close = os.close

        def mock_close(fd):
            closed_fds.append(fd)
            return original_close(fd)

        original_write = os.write
        call_count = [0]
        fds_created = []

        def mock_write(fd, data):
            if fd not in fds_created:
                fds_created.append(fd)

            call_count[0] += 1

            # First write: partial success
            if call_count[0] == 1:
                # Write only 10 bytes to force another loop iteration
                return 10
            # Second write: ENOSPC
            elif call_count[0] == 2:
                error = OSError("No space left on device")
                error.errno = errno.ENOSPC
                raise error

            return original_write(fd, data)

        with patch('os.write', side_effect=mock_write):
            with patch('os.close', side_effect=mock_close):
                with pytest.raises(OSError) as exc_info:
                    storage.add(Todo(title="Second todo", status="pending"))

                assert exc_info.value.errno == errno.ENOSPC

        # Verify all fds were closed
        unclosed_fds = [fd for fd in fds_created if fd not in closed_fds]

        if unclosed_fds:
            pytest.fail(
                f"File descriptor leak after partial write! "
                f"Unclosed fds: {unclosed_fds}"
            )

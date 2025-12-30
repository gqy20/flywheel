"""Test for Issue #66 - File descriptor leak in replace operation.

This test verifies that the file descriptor returned by tempfile.mkstemp()
is properly closed before calling Path.replace(), which is required on Windows
to avoid "file being used" errors.

The bug is in src/flywheel/storage.py around line 112:
- The file descriptor is still open when Path.replace() is called
- This causes resource leaks and failures on Windows
- The fd must be closed BEFORE replace(), not after
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_file_descriptor_closed_before_replace_in_save():
    """Test that _save() closes fd before Path.replace().

    This test uses mocking to verify the correct order of operations:
    1. os.write() and os.fsync() with fd still open
    2. os.close(fd) to close the file descriptor
    3. Path.replace() to atomically replace the file

    The bug was that replace() was called before close(), which causes
    issues on Windows where files cannot be replaced while open.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Track the order of operations
        operations = []

        original_write = os.write
        original_fsync = os.fsync
        original_close = os.close
        original_replace = Path.replace

        def mock_write(fd, data):
            operations.append(('write', fd))
            return original_write(fd, data)

        def mock_fsync(fd):
            operations.append(('fsync', fd))
            return original_fsync(fd)

        def mock_close(fd):
            operations.append(('close', fd))
            return original_close(fd)

        def mock_replace(self, target):
            operations.append(('replace', str(self), str(target)))
            return original_replace(self, target)

        with patch('os.write', side_effect=mock_write):
            with patch('os.fsync', side_effect=mock_fsync):
                with patch('os.close', side_effect=mock_close):
                    with patch('pathlib.Path.replace', side_effect=mock_replace):
                        # Perform a save operation
                        todo = Todo(title="Test todo", status="pending")
                        storage.add(todo)

        # Verify the correct order:
        # 1. write/fsync should happen with fd open
        # 2. close must happen BEFORE replace
        close_indices = [i for i, (op, _) in enumerate(operations) if op == 'close']
        replace_indices = [i for i, (op, _) in enumerate(operations) if op == 'replace']

        # There should be at least one close and one replace
        assert len(close_indices) > 0, "No os.close() call detected"
        assert len(replace_indices) > 0, "No Path.replace() call detected"

        # EVERY replace must happen after at least one close
        for replace_idx in replace_indices:
            # Find the close that corresponds to this operation
            # (they should be paired: each save has one close and one replace)
            assert any(close_idx < replace_idx for close_idx in close_indices), \
                f"Path.replace() called at index {replace_idx} before os.close() at {close_indices}. " \
                "This causes 'file being used' errors on Windows."


def test_file_descriptor_closed_before_replace_in_save_with_todos():
    """Test that _save_with_todos() closes fd before Path.replace()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Track the order of operations
        operations = []

        original_write = os.write
        original_fsync = os.fsync
        original_close = os.close
        original_replace = Path.replace

        def mock_write(fd, data):
            operations.append(('write', fd))
            return original_write(fd, data)

        def mock_fsync(fd):
            operations.append(('fsync', fd))
            return original_fsync(fd)

        def mock_close(fd):
            operations.append(('close', fd))
            return original_close(fd)

        def mock_replace(self, target):
            operations.append(('replace', str(self), str(target)))
            return original_replace(self, target)

        with patch('os.write', side_effect=mock_write):
            with patch('os.fsync', side_effect=mock_fsync):
                with patch('os.close', side_effect=mock_close):
                    with patch('pathlib.Path.replace', side_effect=mock_replace):
                        # Perform operations that use _save_with_todos
                        todo = Todo(title="Test", status="pending")
                        storage.add(todo)
                        storage.update(todo)

        # Verify close happens before replace
        close_indices = [i for i, (op, _) in enumerate(operations) if op == 'close']
        replace_indices = [i for i, (op, _) in enumerate(operations) if op == 'replace']

        assert len(close_indices) > 0, "No os.close() call detected"
        assert len(replace_indices) > 0, "No Path.replace() call detected"

        for replace_idx in replace_indices:
            assert any(close_idx < replace_idx for close_idx in close_indices), \
                f"Path.replace() called at index {replace_idx} before os.close() at {close_indices}"


def test_data_integrity_after_fix():
    """Verify that closing fd before replace doesn't break data integrity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Add multiple todos
        todos = []
        for i in range(3):
            todo = Todo(title=f"Test todo {i}", status="pending")
            added = storage.add(todo)
            todos.append(added)

        # Update a todo
        todos[0].title = "Updated todo 0"
        storage.update(todos[0])

        # Delete a todo
        storage.delete(todos[1].id)

        # Verify all data persisted correctly
        storage2 = Storage(str(storage_path))
        loaded_todos = storage2.list()

        assert len(loaded_todos) == 2
        assert loaded_todos[0].title == "Updated todo 0"
        assert loaded_todos[1].title == "Test todo 2"


def test_file_descriptor_not_leaked():
    """Test that file descriptors don't leak over multiple operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"

        # Get baseline FD count (Linux only)
        if os.path.exists("/proc/self/fd"):
            baseline_fds = set(os.listdir("/proc/self/fd"))
        else:
            baseline_fds = set()

        # Create storage and perform operations
        storage = Storage(str(storage_path))
        for i in range(10):
            todo = Todo(title=f"Test {i}", status="pending")
            storage.add(todo)
            if i % 2 == 0:
                storage.update(todo)
            if i % 3 == 0:
                storage.delete(todo.id)

        # Check FD count hasn't grown significantly
        # (allowing some tolerance for other system operations)
        if os.path.exists("/proc/self/fd"):
            current_fds = set(os.listdir("/proc/self/fd"))
            # More than 5 new FDs would indicate a leak
            leaked_fds = current_fds - baseline_fds
            assert len(leaked_fds) <= 5, \
                f"Potential file descriptor leak: {len(leaked_fds)} FDs may have leaked"

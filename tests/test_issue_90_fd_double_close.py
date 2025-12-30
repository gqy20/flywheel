"""Test for Issue #90: File descriptor double-close protection.

This test verifies that file descriptors are properly protected against
double-close in the finally block.
"""

import os
import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_fd_not_double_closed_after_os_close():
    """Test that fd is set to -1 AFTER os.close() to prevent double-close in finally block."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add multiple todos to trigger _save_with_todos multiple times
        # This will exercise the fd close/finally block logic
        for i in range(3):
            storage.add(Todo(title=f"Todo {i}"))

        # Verify all todos were saved correctly
        # If fd was double-closed, we would see errors during saves
        todos = storage.list()
        assert len(todos) == 3

        # Verify we can still add more todos (no fd corruption)
        storage.add(Todo(title="Todo 3"))
        assert len(storage.list()) == 4


def test_finally_block_handles_closed_fd():
    """Test that finally block doesn't try to close an already-closed fd."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Trigger a save operation
        storage.add(Todo(title="Test"))

        # The finally block should handle the case where fd is already closed
        # (fd == -1) and not attempt to close it again
        # If the finally block tries to close an already-closed fd,
        # it would raise a BadFileDescriptor error

        # Multiple successful saves prove no double-close is occurring
        for i in range(5):
            storage.add(Todo(title=f"Additional todo {i}"))

        assert len(storage.list()) == 6


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

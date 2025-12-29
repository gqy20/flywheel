"""Test for file descriptor leak issue #18."""

import os
import resource
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def get_open_fds():
    """Get the number of open file descriptors."""
    # Get soft limit of open file descriptors
    soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    # Count open file descriptors in /proc/self/fd
    fd_dir = Path('/proc/self/fd')
    if fd_dir.exists():
        return len(list(fd_dir.iterdir()))
    # Fallback: use lsof if available (less reliable)
    return None


def test_no_fd_leak_on_save():
    """Test that _save doesn't leak file descriptors."""
    # Skip if we can't count FDs
    if not Path('/proc/self/fd').exists():
        pytest.skip("Cannot count file descriptors on this system")

    # Create a temporary storage
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Get initial FD count
        initial_fds = get_open_fds()
        assert initial_fds is not None

        # Perform multiple save operations
        for i in range(10):
            todo = Todo(id=i+1, title=f"Todo {i+1}", description=f"Description {i+1}")
            storage._todos.append(todo)
            storage._save()

        # Get final FD count
        final_fds = get_open_fds()

        # FD count should not increase significantly (allow small margin for error)
        # If there's a leak, we'd see 10+ extra FDs
        assert final_fds <= initial_fds + 2, \
            f"Potential FD leak: initial={initial_fds}, final={final_fds}"


def test_no_fd_leak_on_save_with_todos():
    """Test that _save_with_todos doesn't leak file descriptors."""
    # Skip if we can't count FDs
    if not Path('/proc/self/fd').exists():
        pytest.skip("Cannot count file descriptors on this system")

    # Create a temporary storage
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Get initial FD count
        initial_fds = get_open_fds()
        assert initial_fds is not None

        # Perform multiple save operations
        for i in range(10):
            todos = [Todo(id=j+1, title=f"Todo {j+1}") for j in range(i+1)]
            storage._save_with_todos(todos)

        # Get final FD count
        final_fds = get_open_fds()

        # FD count should not increase significantly
        assert final_fds <= initial_fds + 2, \
            f"Potential FD leak: initial={initial_fds}, final={final_fds}"


def test_no_fd_leak_on_add():
    """Test that add operations don't leak file descriptors."""
    if not Path('/proc/self/fd').exists():
        pytest.skip("Cannot count file descriptors on this system")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        initial_fds = get_open_fds()
        assert initial_fds is not None

        # Add multiple todos
        for i in range(10):
            todo = Todo(id=i+1, title=f"Todo {i+1}")
            storage.add(todo)

        final_fds = get_open_fds()
        assert final_fds <= initial_fds + 2, \
            f"Potential FD leak: initial={initial_fds}, final={final_fds}"


def test_no_fd_leak_on_update():
    """Test that update operations don't leak file descriptors."""
    if not Path('/proc/self/fd').exists():
        pytest.skip("Cannot count file descriptors on this system")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo first
        todo = Todo(id=1, title="Test todo")
        storage.add(todo)

        initial_fds = get_open_fds()
        assert initial_fds is not None

        # Update multiple times
        for i in range(10):
            todo.title = f"Updated todo {i}"
            storage.update(todo)

        final_fds = get_open_fds()
        assert final_fds <= initial_fds + 2, \
            f"Potential FD leak: initial={initial_fds}, final={final_fds}"


def test_no_fd_leak_on_delete():
    """Test that delete operations don't leak file descriptors."""
    if not Path('/proc/self/fd').exists():
        pytest.skip("Cannot count file descriptors on this system")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add multiple todos
        for i in range(10):
            todo = Todo(id=i+1, title=f"Todo {i+1}")
            storage.add(todo)

        initial_fds = get_open_fds()
        assert initial_fds is not None

        # Delete multiple todos
        for i in range(1, 6):
            storage.delete(i)

        final_fds = get_open_fds()
        assert final_fds <= initial_fds + 2, \
            f"Potential FD leak: initial={initial_fds}, final={final_fds}"

"""Test context manager support for storage lifecycle (Issue #707)."""
import tempfile
import os
from pathlib import Path
from flywheel.storage import FileStorage
from flywheel import Todo


def test_context_manager_closes_on_normal_exit():
    """Test that FileStorage closes properly when exiting context normally."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")

        # Use FileStorage as a context manager
        with FileStorage(storage_path) as storage:
            # Add a todo
            storage.add(Todo(title="Test task"))

            # Verify storage is not closed yet
            assert not hasattr(storage, '_closed') or not storage._closed

        # After exiting context, storage should be closed
        assert storage._closed, "Storage should be closed after exiting context"


def test_context_manager_closes_on_exception():
    """Test that FileStorage closes properly even when exception occurs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")

        storage = None
        try:
            # Use FileStorage as a context manager with exception
            with FileStorage(storage_path) as storage:
                # Add a todo
                storage.add(Todo(title="Test task"))

                # Raise an exception
                raise ValueError("Test exception")
        except ValueError:
            pass

        # After exiting context with exception, storage should still be closed
        assert storage._closed, "Storage should be closed even when exception occurs"


def test_context_manager_saves_dirty_data():
    """Test that context manager saves dirty data before closing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")

        # Use FileStorage as a context manager
        with FileStorage(storage_path) as storage:
            storage.add(Todo(title="Test task"))
            # Data should be dirty (not yet saved)

        # After context exits, data should be saved to disk
        # Create a new storage instance to verify
        storage2 = FileStorage(storage_path)
        todos = storage2.list()
        assert len(todos) == 1
        assert todos[0].title == "Test task"
        storage2.close()


def test_context_manager_returns_self():
    """Test that context manager __enter__ returns self."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")

        storage = FileStorage(storage_path)
        # Use context manager
        with storage as ctx:
            # Context manager should return the storage instance itself
            assert ctx is storage

        storage.close()


def test_context_manager_stops_auto_save_thread():
    """Test that context manager stops the auto-save background thread."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")

        with FileStorage(storage_path) as storage:
            # Auto-save thread should be running
            assert storage._auto_save_thread.is_alive()

        # After exiting context, auto-save thread should be stopped
        assert not storage._auto_save_thread.is_alive(), "Auto-save thread should be stopped after context exit"

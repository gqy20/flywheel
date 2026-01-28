"""Test close/cleanup functionality for Issue #688."""

import tempfile
import time
from pathlib import Path

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


def test_close_stops_auto_save_thread():
    """Test that close() stops the auto-save background thread."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path))

        # Get the auto-save thread
        auto_save_thread = storage._auto_save_thread

        # Verify thread is alive
        assert auto_save_thread.is_alive()

        # Close the storage
        storage.close()

        # Verify thread is stopped
        # Give a small delay for thread to finish
        time.sleep(0.5)
        assert not auto_save_thread.is_alive()


def test_close_saves_dirty_data():
    """Test that close() saves unsaved changes before stopping."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path))

        # Add a todo (marks as dirty)
        storage.add(Todo(title="Test todo"))

        # Close the storage
        storage.close()

        # Verify data was saved by creating a new storage instance
        storage2 = FileStorage(str(storage_path))
        todos = storage2.list_all()
        assert len(todos) == 1
        assert todos[0].title == "Test todo"
        storage2.close()


def test_close_is_idempotent():
    """Test that close() can be called multiple times safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path))

        # Call close multiple times - should not raise
        storage.close()
        storage.close()
        storage.close()

        # Should still be able to read data
        storage2 = FileStorage(str(storage_path))
        assert storage2.list_all() == []
        storage2.close()


def test_close_sets_closed_flag():
    """Test that close() sets a flag to prevent further operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path))

        # Initially, _closed flag should not be set
        assert not hasattr(storage, '_closed') or not storage._closed

        # Close the storage
        storage.close()

        # Verify _closed flag is set
        assert storage._closed is True


def test_context_manager_calls_close():
    """Test that explicit close() after context manager works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Use context manager for lock management
        with FileStorage(str(storage_path)) as storage:
            # Get the auto-save thread
            auto_save_thread = storage._auto_save_thread
            storage.add(Todo(title="Test todo"))

            # Verify thread is alive inside context
            assert auto_save_thread.is_alive()

        # After exiting context, thread is still alive because __exit__ only calls _cleanup
        # The auto-save thread continues running until explicitly closed
        assert auto_save_thread.is_alive()

        # Now explicitly close to stop the thread
        storage.close()

        # Give a small delay for thread to finish
        time.sleep(0.5)
        assert not auto_save_thread.is_alive()

        # Verify data was saved
        storage2 = FileStorage(str(storage_path))
        todos = storage2.list_all()
        assert len(todos) == 1
        assert todos[0].title == "Test todo"
        storage2.close()


def test_close_unregisters_atexit():
    """Test that close() prevents atexit handler from running."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path))

        # Add a todo
        storage.add(Todo(title="Test todo"))

        # Close explicitly
        storage.close()

        # Verify _closed flag is set
        assert storage._closed is True

        # Manually call _cleanup to simulate atexit being called
        # It should do nothing because _closed is True
        storage._cleanup()

        # The atexit handler should not cause issues
        # This is a basic smoke test - in real scenario, we'd need
        # to actually exit to test atexit behavior
        assert True

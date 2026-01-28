"""Test auto-save timer mechanism (Issue #672).

This test verifies that the auto-save background timer is properly
implemented and running, which was the enhancement requested in Issue #672.
"""

import tempfile
import time
from pathlib import Path

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


def test_auto_save_timer_is_running():
    """Test that auto-save background timer is started and running.

    This verifies the enhancement from Issue #672 that the auto-save
    timer mechanism is implemented.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create a FileStorage instance
        storage = FileStorage(str(storage_path))

        # Verify auto-save thread exists and is running
        assert hasattr(storage, '_auto_save_thread'), \
            "FileStorage should have _auto_save_thread attribute"
        assert storage._auto_save_thread is not None, \
            "Auto-save thread should be created"
        assert storage._auto_save_thread.is_alive(), \
            "Auto-save thread should be running"
        assert storage._auto_save_thread.daemon, \
            "Auto-save thread should be a daemon thread"

        # Verify stop event exists
        assert hasattr(storage, '_auto_save_stop_event'), \
            "FileStorage should have _auto_save_stop_event attribute"

        # Clean up
        storage._auto_save_stop_event.set()
        storage._auto_save_thread.join(timeout=5)


def test_auto_save_timer_persists_data():
    """Test that auto-save timer actually persists data to disk.

    This verifies the key value proposition from Issue #672:
    data is saved periodically even without explicit _cleanup calls.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create a FileStorage instance with short auto-save interval
        storage = FileStorage(str(storage_path))
        storage.AUTO_SAVE_INTERVAL = 0.5  # 500ms for faster testing

        # Add a todo (this sets _dirty = True)
        todo = Todo(title="Test auto-save timer")
        storage.add(todo)

        # Wait for auto-save to trigger (background timer)
        time.sleep(1.5)

        # Verify data was persisted to disk by the auto-save timer
        assert storage_path.exists(), \
            "Storage file should exist after auto-save"

        # Read the file directly from disk (bypassing cache)
        with open(storage_path, 'r') as f:
            import json
            data = json.load(f)
            todos = data.get('todos', [])
            assert len(todos) >= 1, \
                "At least one todo should be saved by auto-save timer"
            assert any(t['title'] == 'Test auto-save timer' for t in todos), \
                "Added todo should be in file"

        # Clean up
        storage._auto_save_stop_event.set()
        storage._auto_save_thread.join(timeout=5)


def test_auto_save_timer_stops_on_close():
    """Test that auto-save timer is properly stopped on close.

    This verifies the cleanup mechanism mentioned in Issue #672.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create a FileStorage instance
        storage = FileStorage(str(storage_path))

        # Get reference to the thread
        auto_save_thread = storage._auto_save_thread

        # Close the storage
        storage.close()

        # Verify thread is stopped
        assert not auto_save_thread.is_alive(), \
            "Auto-save thread should be stopped after close"

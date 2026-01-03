"""Test auto-save mechanism (Issue #592)."""

import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


class TestAutoSaveMechanism:
    """Test auto-save background thread functionality."""

    def test_auto_save_thread_started_on_init(self):
        """Test that auto-save thread is started when FileStorage is initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create a FileStorage instance
            storage = FileStorage(str(storage_path))

            # Check that auto-save thread exists and is alive
            assert hasattr(storage, '_auto_save_thread'), "FileStorage should have _auto_save_thread attribute"
            assert storage._auto_save_thread is not None, "Auto-save thread should be created"
            assert storage._auto_save_thread.is_alive(), "Auto-save thread should be running"
            assert storage._auto_save_thread.daemon, "Auto-save thread should be a daemon thread"

            # Clean up
            storage._auto_save_stop_event.set()
            storage._auto_save_thread.join(timeout=5)

    def test_auto_save_triggers_save_when_dirty(self):
        """Test that auto-save triggers _save() when _dirty is True and interval passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create a FileStorage instance with a short auto-save interval
            storage = FileStorage(str(storage_path))
            original_interval = storage.AUTO_SAVE_INTERVAL
            storage.AUTO_SAVE_INTERVAL = 0.5  # 500ms for faster testing

            # Mock the _save method to track calls
            save_mock = Mock(wraps=storage._save)
            storage._save = save_mock

            # Mark storage as dirty
            storage._dirty = True
            storage.last_saved_time = time.time() - original_interval - 1  # Force save condition

            # Wait for auto-save to trigger
            time.sleep(1)

            # Verify _save was called
            assert save_mock.called, "_save() should be called by auto-save thread when _dirty is True"

            # Clean up
            storage._auto_save_stop_event.set()
            storage._auto_save_thread.join(timeout=5)

    def test_auto_save_skips_when_not_dirty(self):
        """Test that auto-save does not trigger _save() when _dirty is False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create a FileStorage instance with a short auto-save interval
            storage = FileStorage(str(storage_path))
            storage.AUTO_SAVE_INTERVAL = 0.5  # 500ms for faster testing

            # Mock the _save method to track calls
            save_mock = Mock(wraps=storage._save)
            storage._save = save_mock

            # Ensure storage is NOT dirty
            storage._dirty = False
            storage.last_saved_time = time.time() - 100  # Force time condition

            # Wait for auto-save to check
            time.sleep(1)

            # Verify _save was NOT called
            assert not save_mock.called, "_save() should not be called by auto-save thread when _dirty is False"

            # Clean up
            storage._auto_save_stop_event.set()
            storage._auto_save_thread.join(timeout=5)

    def test_auto_save_persists_data_to_disk(self):
        """Test that auto-save actually persists data to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create a FileStorage instance with a short auto-save interval
            storage = FileStorage(str(storage_path))
            storage.AUTO_SAVE_INTERVAL = 0.5  # 500ms for faster testing

            # Add a todo (this will set _dirty = True)
            todo = Todo(title="Test auto-save")
            storage.add(todo)

            # Wait for auto-save to trigger
            time.sleep(1.5)

            # Verify data was persisted to disk
            assert storage_path.exists(), "Storage file should exist after auto-save"

            with open(storage_path, 'r') as f:
                data = json.load(f)
                todos = data.get('todos', [])
                assert len(todos) >= 1, "At least one todo should be saved"
                assert any(t['title'] == 'Test auto-save' for t in todos), "Added todo should be in file"

            # Clean up
            storage._auto_save_stop_event.set()
            storage._auto_save_thread.join(timeout=5)

    def test_auto_save_respects_interval(self):
        """Test that auto-save respects the AUTO_SAVE_INTERVAL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create a FileStorage instance with a longer auto-save interval
            storage = FileStorage(str(storage_path))
            storage.AUTO_SAVE_INTERVAL = 2.0  # 2 seconds

            # Mock the _save method to track calls
            save_mock = Mock(wraps=storage._save)
            storage._save = save_mock

            # Mark storage as dirty and update last_saved_time
            storage._dirty = True
            storage.last_saved_time = time.time()

            # Wait for less than the interval
            time.sleep(1)

            # Verify _save was NOT called yet
            assert not save_mock.called, "_save() should not be called before AUTO_SAVE_INTERVAL elapses"

            # Clean up
            storage._auto_save_stop_event.set()
            storage._auto_save_thread.join(timeout=5)

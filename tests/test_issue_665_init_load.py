"""Test that __init__ loads data from storage file.

This test verifies issue #665 - the __init__ method should load data
from the storage file to prevent data loss after restart.

Issue: #665
"""

import json
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestInitLoadsData:
    """Verify __init__ loads data from storage file."""

    def test_init_loads_existing_todos_from_file(self):
        """Test that __init__ loads existing todos from storage file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"

            # Create a storage file with test data using first instance
            storage1 = Storage(str(storage_path))
            storage1.add(Todo(title="Task 1", status="pending"))
            storage1.add(Todo(title="Task 2", status="completed"))

            # Verify first instance has the data
            assert len(storage1.list()) == 2
            assert storage1.get(1).title == "Task 1"
            assert storage1.get(2).title == "Task 2"

            # Create a new Storage instance - should load the data
            storage2 = Storage(str(storage_path))

            # Verify second instance loaded the data from file
            assert len(storage2.list()) == 2, "Second instance should load todos from file"
            assert storage2.get(1).title == "Task 1", "First todo should be loaded"
            assert storage2.get(2).title == "Task 2", "Second todo should be loaded"

    def test_init_loads_next_id_from_file(self):
        """Test that __init__ loads next_id from storage file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"

            # Create a storage file with test data
            storage1 = Storage(str(storage_path))
            storage1.add(Todo(title="Task 1", status="pending"))
            storage1.add(Todo(title="Task 2", status="completed"))
            storage1.add(Todo(title="Task 3", status="pending"))

            # Delete one todo to create a gap
            storage1.delete(2)

            # next_id should be 4 (not affected by deletion)
            assert storage1.get_next_id() == 4

            # Create a new Storage instance - should load next_id
            storage2 = Storage(str(storage_path))

            # Verify next_id was loaded correctly
            assert storage2.get_next_id() == 4, "next_id should be loaded from file"

    def test_init_initializes_empty_state_when_file_missing(self):
        """Test that __init__ initializes empty state when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "nonexistent.json"

            # Create storage for non-existent file
            storage = Storage(str(storage_path))

            # Verify empty state was initialized
            assert len(storage.list()) == 0, "Should have empty todo list"
            assert storage.get_next_id() == 1, "Should start with next_id=1"

    def test_init_preserves_data_across_restarts(self):
        """Test that __init__ preserves data across application restarts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"

            # Simulate first application run
            app1 = Storage(str(storage_path))
            app1.add(Todo(title="Important Task", status="pending"))
            app1.add(Todo(title="Another Task", status="completed"))

            # "Restart" application by creating new Storage instance
            app2 = Storage(str(storage_path))

            # Verify all data preserved after restart
            todos = app2.list()
            assert len(todos) == 2, "All todos should be preserved"
            assert any(t.title == "Important Task" for t in todos), "Tasks should be preserved"
            assert any(t.title == "Another Task" for t in todos), "Tasks should be preserved"

    def test_init_calls_load_sync_during_initialization(self):
        """Test that __init__ calls _load_sync to load data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"

            # Create a file with data
            test_data = {
                "todos": [
                    {"id": 1, "title": "Pre-existing Task", "status": "pending"},
                ],
                "next_id": 2,
                "metadata": {"checksum": "ignored"}
            }

            with storage_path.open("w") as f:
                json.dump(test_data, f)

            # Create Storage - __init__ should call _load_sync
            storage = Storage(str(storage_path))

            # Verify data was loaded during initialization
            assert len(storage.list()) == 1, "Data should be loaded during __init__"
            assert storage.get(1).title == "Pre-existing Task"
            assert storage.get_next_id() == 2

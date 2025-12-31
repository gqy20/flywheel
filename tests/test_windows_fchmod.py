"""Test for Windows compatibility - os.fchmod not available."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestWindowsFchmodCompatibility(unittest.TestCase):
    """Test that storage works on Windows where os.fchmod is not available."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "test_todos.json"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.storage_path.exists():
            self.storage_path.unlink()
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_save_works_without_fchmod(self):
        """Test that _save works when os.fchmod is not available (Windows)."""
        # Create a storage instance
        storage = Storage(str(self.storage_path))

        # Mock os.fchmod to raise AttributeError (simulating Windows)
        with patch.object(os, 'fchmod', side_effect=AttributeError("fchmod not available")):
            # Add a todo - this should not fail even without fchmod
            todo = Todo(title="Test todo", status="pending")
            added_todo = storage.add(todo)

            # Verify the todo was added
            self.assertIsNotNone(added_todo)
            self.assertEqual(added_todo.title, "Test todo")
            self.assertEqual(added_todo.status, "pending")

        # Verify the todo was persisted correctly
        storage2 = Storage(str(self.storage_path))
        retrieved_todo = storage2.get(added_todo.id)
        self.assertIsNotNone(retrieved_todo)
        self.assertEqual(retrieved_todo.title, "Test todo")

    def test_save_with_todos_works_without_fchmod(self):
        """Test that _save_with_todos works when os.fchmod is not available (Windows)."""
        storage = Storage(str(self.storage_path))

        # Mock os.fchmod to raise AttributeError (simulating Windows)
        with patch.object(os, 'fchmod', side_effect=AttributeError("fchmod not available")):
            # Add multiple todos
            todo1 = Todo(title="Todo 1", status="pending")
            todo2 = Todo(title="Todo 2", status="completed")

            added1 = storage.add(todo1)
            added2 = storage.add(todo2)

            # Update a todo
            updated = Todo(id=added1.id, title="Updated Todo 1", status="completed")
            storage.update(updated)

        # Verify all changes were persisted
        storage2 = Storage(str(self.storage_path))
        todos = storage2.list()
        self.assertEqual(len(todos), 2)

        retrieved1 = storage2.get(added1.id)
        self.assertEqual(retrieved1.title, "Updated Todo 1")
        self.assertEqual(retrieved1.status, "completed")

        retrieved2 = storage2.get(added2.id)
        self.assertEqual(retrieved2.title, "Todo 2")


if __name__ == '__main__':
    unittest.main()

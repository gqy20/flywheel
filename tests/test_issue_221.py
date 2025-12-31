"""Test for issue #221 - Windows fchmod fallback.

This test verifies that when os.fchmod is not available (as on Windows),
the code properly falls back to os.chmod to set restrictive permissions.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestIssue221WindowsFchmodFallback(unittest.TestCase):
    """Test that Windows fchmod fallback sets permissions correctly."""

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

    def test_save_falls_back_to_chmod_when_fchmod_not_available(self):
        """Test that _save falls back to os.chmod when os.fchmod raises AttributeError."""
        storage = Storage(str(self.storage_path))

        # Track whether os.chmod was called
        original_chmod = os.chmod
        chmod_called = []
        chmod_permissions = []

        def mock_chmod(path, mode):
            chmod_called.append(path)
            chmod_permissions.append(mode)
            return original_chmod(path, mode)

        # Mock os.fchmod to raise AttributeError (simulating Windows)
        with patch.object(os, 'fchmod', side_effect=AttributeError("fchmod not available")):
            with patch.object(os, 'chmod', side_effect=mock_chmod):
                # Add a todo - this should trigger the fallback to os.chmod
                todo = Todo(title="Test todo", status="pending")
                added_todo = storage.add(todo)

                # Verify os.chmod was called as a fallback
                self.assertEqual(len(chmod_called), 1,
                                 "os.chmod should be called once as fallback when fchmod is not available")

                # Verify the permissions were set to 0o600 (user read/write only)
                self.assertEqual(chmod_permissions[0], 0o600,
                                 "os.chmod should be called with 0o600 permissions")

        # Verify the todo was added successfully
        self.assertIsNotNone(added_todo)
        self.assertEqual(added_todo.title, "Test todo")

        # Verify the todo was persisted
        storage2 = Storage(str(self.storage_path))
        retrieved_todo = storage2.get(added_todo.id)
        self.assertIsNotNone(retrieved_todo)
        self.assertEqual(retrieved_todo.title, "Test todo")

    def test_save_with_todos_falls_back_to_chmod_when_fchmod_not_available(self):
        """Test that _save_with_todos falls back to os.chmod when os.fchmod raises AttributeError."""
        storage = Storage(str(self.storage_path))

        # Track whether os.chmod was called
        original_chmod = os.chmod
        chmod_called = []
        chmod_permissions = []

        def mock_chmod(path, mode):
            chmod_called.append(path)
            chmod_permissions.append(mode)
            return original_chmod(path, mode)

        # Mock os.fchmod to raise AttributeError (simulating Windows)
        with patch.object(os, 'fchmod', side_effect=AttributeError("fchmod not available")):
            with patch.object(os, 'chmod', side_effect=mock_chmod):
                # Add multiple todos
                todo1 = Todo(title="Todo 1", status="pending")
                todo2 = Todo(title="Todo 2", status="completed")

                added1 = storage.add(todo1)
                added2 = storage.add(todo2)

                # Update a todo
                updated = Todo(id=added1.id, title="Updated Todo 1", status="completed")
                storage.update(updated)

                # Verify os.chmod was called for each save operation
                # We expect at least 3 calls: one for each add and one for update
                self.assertGreaterEqual(len(chmod_called), 3,
                                        "os.chmod should be called for each save operation")

                # Verify all calls used 0o600 permissions
                for perm in chmod_permissions:
                    self.assertEqual(perm, 0o600,
                                     "All os.chmod calls should use 0o600 permissions")

        # Verify all changes were persisted
        storage2 = Storage(str(self.storage_path))
        todos = storage2.list()
        self.assertEqual(len(todos), 2)

    def test_delete_falls_back_to_chmod_when_fchmod_not_available(self):
        """Test that delete operation falls back to os.chmod when os.fchmod raises AttributeError."""
        storage = Storage(str(self.storage_path))

        # Add a todo first
        todo = Todo(title="Test todo", status="pending")
        added = storage.add(todo)

        # Track whether os.chmod was called
        original_chmod = os.chmod
        chmod_called = []

        def mock_chmod(path, mode):
            chmod_called.append(True)
            return original_chmod(path, mode)

        # Mock os.fchmod to raise AttributeError (simulating Windows)
        with patch.object(os, 'fchmod', side_effect=AttributeError("fchmod not available")):
            with patch.object(os, 'chmod', side_effect=mock_chmod):
                # Delete the todo
                result = storage.delete(added.id)

                # Verify os.chmod was called during save
                self.assertTrue(len(chmod_called) > 0,
                                "os.chmod should be called when fchmod is not available")

                # Verify deletion was successful
                self.assertTrue(result)

        # Verify the todo was deleted
        storage2 = Storage(str(self.storage_path))
        retrieved = storage2.get(added.id)
        self.assertIsNone(retrieved)


if __name__ == '__main__':
    unittest.main()

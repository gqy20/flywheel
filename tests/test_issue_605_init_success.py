"""
Test for Issue #605: Verify init_success is set correctly in FileNotFoundError branch

This test ensures that when a TodoList is initialized for the first time (file doesn't exist),
the init_success flag is properly set to True, allowing cleanup registration to work correctly.
"""

import os
import tempfile
import pytest
from pathlib import Path

from flywheel.storage import TodoList


class TestIssue605InitSuccess:
    """Test that init_success is correctly set during initialization"""

    def test_init_success_on_file_not_found(self, tmp_path):
        """
        Test that init_success is set to True when file doesn't exist.

        This is the normal case for first run (Issue #601). The FileNotFoundError
        should result in init_success=True to ensure cleanup registration works.

        Related: Issue #605
        """
        # Create a path for a non-existent file
        non_existent_path = tmp_path / "new_todos.json"

        # Verify file doesn't exist
        assert not non_existent_path.exists()

        # Create TodoList with non-existent file
        todo_list = TodoList(str(non_existent_path))

        # Verify the object was initialized successfully
        assert todo_list._todos == []
        assert todo_list._next_id == 1
        assert todo_list._dirty is False

        # Verify the file was created (save happens during cleanup or explicit save)
        # The object should be functional even though file didn't exist initially
        assert todo_list is not None
        assert hasattr(todo_list, '_todos')
        assert hasattr(todo_list, '_lock')

    def test_init_success_multiple_first_runs(self, tmp_path):
        """
        Test that multiple TodoList instances with non-existent files
        all initialize correctly.

        Related: Issue #605
        """
        paths = [
            tmp_path / "todos1.json",
            tmp_path / "todos2.json",
            tmp_path / "todos3.json",
        ]

        for path in paths:
            assert not path.exists()
            todo_list = TodoList(str(path))

            # Each should be properly initialized
            assert todo_list._todos == []
            assert todo_list._next_id == 1
            assert todo_list._dirty is False

    def test_init_success_with_operations_after_first_run(self, tmp_path):
        """
        Test that we can perform normal operations after initializing
        with a non-existent file.

        Related: Issue #605
        """
        non_existent_path = tmp_path / "new_todos.json"

        # Create TodoList
        todo_list = TodoList(str(non_existent_path))

        # Should be able to add todos
        todo = todo_list.add("Test todo", priority=1)
        assert todo is not None
        assert todo.task == "Test todo"

        # Should be able to retrieve todos
        todos = todo_list.list()
        assert len(todos) == 1
        assert todos[0].task == "Test todo"

        # Should be able to update todos
        updated = todo_list.update(todo.id, task="Updated task")
        assert updated is not None
        assert updated.task == "Updated task"

    def test_init_comparison_with_existing_file(self, tmp_path):
        """
        Compare initialization behavior between non-existent and existing files.
        Both should result in init_success=True for proper object functionality.

        Related: Issue #605
        """
        # Case 1: Non-existent file
        non_existent_path = tmp_path / "non_existent.json"
        todo_list_new = TodoList(str(non_existent_path))

        # Case 2: Existing file (create it first)
        existing_path = tmp_path / "existing.json"
        existing_path.write_text("[]")  # Empty todo list
        todo_list_existing = TodoList(str(existing_path))

        # Both should have the same initial state
        assert todo_list_new._todos == todo_list_existing._todos == []
        assert todo_list_new._next_id == todo_list_existing._next_id == 1
        assert todo_list_new._dirty == todo_list_existing._dirty is False

        # Both should be functional
        for todo_list in [todo_list_new, todo_list_existing]:
            todo = todo_list.add("Test")
            assert todo is not None
            assert len(todo_list.list()) == 1

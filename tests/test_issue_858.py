"""Test bulk operation alias methods (Issue #858).

This test file verifies that the storage implementations provide
alias methods add_many, update_many, and delete_many that are
convenience aliases for add_batch, update_batch, and delete_batch.
"""

import pytest
from pathlib import Path
from flywheel import Todo, FileStorage


class TestBulkOperationAliases:
    """Test suite for bulk operation alias methods."""

    def test_filestorage_has_add_many_method(self):
        """FileStorage should have add_many method as an alias for add_batch."""
        storage = FileStorage()
        assert hasattr(storage, 'add_many'), "FileStorage should have add_many method"
        assert callable(storage.add_many), "add_many should be callable"

    def test_filestorage_has_delete_many_method(self):
        """FileStorage should have delete_many method as an alias for delete_batch."""
        storage = FileStorage()
        assert hasattr(storage, 'delete_many'), "FileStorage should have delete_many method"
        assert callable(storage.delete_many), "delete_many should be callable"

    def test_filestorage_has_update_many_method(self):
        """FileStorage should have update_many method as an alias for update_batch."""
        storage = FileStorage()
        assert hasattr(storage, 'update_many'), "FileStorage should have update_many method"
        assert callable(storage.update_many), "update_many should be callable"

    def test_add_many_basic_functionality(self):
        """Test that add_many works like add_batch."""
        storage = FileStorage()

        todos = [
            Todo(title="Task 1"),
            Todo(title="Task 2"),
            Todo(title="Task 3"),
        ]

        result = storage.add_many(todos)

        assert len(result) == 3
        assert all(isinstance(todo, Todo) for todo in result)
        assert all(todo.id is not None for todo in result)
        assert [todo.title for todo in result] == ["Task 1", "Task 2", "Task 3"]

    def test_add_many_with_empty_list(self):
        """Test that add_many handles empty list correctly."""
        storage = FileStorage()

        result = storage.add_many([])

        assert result == []

    def test_delete_many_multiple_todos(self):
        """Test that delete_many works like delete_batch."""
        storage = FileStorage()

        # Add some todos first
        todos = [
            Todo(title="Task 1"),
            Todo(title="Task 2"),
            Todo(title="Task 3"),
        ]
        added = storage.add_many(todos)

        # Delete two of them
        ids_to_delete = [added[0].id, added[1].id]
        result = storage.delete_many(ids_to_delete)

        assert len(result) == 2
        assert all(result)  # All should be True (successfully deleted)

        # Verify only the last todo remains
        remaining = storage.list()
        assert len(remaining) == 1
        assert remaining[0].title == "Task 3"

    def test_delete_many_with_nonexistent_ids(self):
        """Test delete_many with some non-existent IDs."""
        storage = FileStorage()

        # Add a todo
        todo = Todo(title="Task 1")
        added = storage.add(todo)

        # Try to delete the existing todo and a non-existent one
        result = storage.delete_many([added.id, 999])

        assert len(result) == 2
        assert result[0] is True  # First one exists and was deleted
        assert result[1] is False  # Second one doesn't exist

    def test_delete_many_with_empty_list(self):
        """Test that delete_many handles empty list correctly."""
        storage = FileStorage()

        result = storage.delete_many([])

        assert result == []

    def test_update_many_multiple_todos(self):
        """Test that update_many works like update_batch."""
        storage = FileStorage()

        # Add some todos first
        todos = [
            Todo(title="Task 1"),
            Todo(title="Task 2"),
            Todo(title="Task 3"),
        ]
        added = storage.add_many(todos)

        # Update them
        updated_todos = [
            Todo(id=added[0].id, title="Updated Task 1"),
            Todo(id=added[1].id, title="Updated Task 2"),
        ]
        result = storage.update_many(updated_todos)

        assert len(result) == 2
        assert all(isinstance(todo, Todo) for todo in result)
        assert [todo.title for todo in result] == ["Updated Task 1", "Updated Task 2"]

        # Verify the updates
        todo1 = storage.get(added[0].id)
        todo2 = storage.get(added[1].id)
        assert todo1.title == "Updated Task 1"
        assert todo2.title == "Updated Task 2"

    def test_update_many_with_empty_list(self):
        """Test that update_many handles empty list correctly."""
        storage = FileStorage()

        result = storage.update_many([])

        assert result == []

    def test_add_many_matches_add_batch(self):
        """Test that add_many produces same results as add_batch."""
        storage = FileStorage()

        todos = [
            Todo(title="Task A"),
            Todo(title="Task B"),
        ]

        # Use add_many
        result_many = storage.add_many(todos)

        # Clear and use add_batch
        storage._todos.clear()
        storage._next_id = 1
        result_batch = storage.add_batch(todos)

        # Results should be equivalent (same structure)
        assert len(result_many) == len(result_batch)
        assert [t.title for t in result_many] == [t.title for t in result_batch]


class TestAsyncBulkOperationAliases:
    """Test suite for async bulk operation alias methods."""

    @pytest.mark.asyncio
    async def test_filestorage_has_async_add_many_method(self):
        """FileStorage should have async_add_many method as an alias for async_add_batch."""
        storage = FileStorage()
        assert hasattr(storage, 'async_add_many'), "FileStorage should have async_add_many method"
        import inspect
        assert inspect.iscoroutinefunction(storage.async_add_many), "async_add_many should be a coroutine"

    @pytest.mark.asyncio
    async def test_filestorage_has_async_delete_many_method(self):
        """FileStorage should have async_delete_many method as an alias for async_delete_batch."""
        storage = FileStorage()
        assert hasattr(storage, 'async_delete_many'), "FileStorage should have async_delete_many method"
        import inspect
        assert inspect.iscoroutinefunction(storage.async_delete_many), "async_delete_many should be a coroutine"

    @pytest.mark.asyncio
    async def test_filestorage_has_async_update_many_method(self):
        """FileStorage should have async_update_many method as an alias for async_update_batch."""
        storage = FileStorage()
        assert hasattr(storage, 'async_update_many'), "FileStorage should have async_update_many method"
        import inspect
        assert inspect.iscoroutinefunction(storage.async_update_many), "async_update_many should be a coroutine"

    @pytest.mark.asyncio
    async def test_async_add_many_basic_functionality(self):
        """Test that async_add_many works like async_add_batch."""
        storage = FileStorage()

        todos = [
            Todo(title="Async Task 1"),
            Todo(title="Async Task 2"),
        ]

        result = await storage.async_add_many(todos)

        assert len(result) == 2
        assert all(isinstance(todo, Todo) for todo in result)
        assert all(todo.id is not None for todo in result)

    @pytest.mark.asyncio
    async def test_async_delete_many_multiple_todos(self):
        """Test that async_delete_many works like async_delete_batch."""
        storage = FileStorage()

        # Add some todos first
        todos = [
            Todo(title="Async Task 1"),
            Todo(title="Async Task 2"),
        ]
        added = await storage.async_add_many(todos)

        # Delete them
        ids_to_delete = [added[0].id, added[1].id]
        result = await storage.async_delete_many(ids_to_delete)

        assert len(result) == 2
        assert all(result)

    @pytest.mark.asyncio
    async def test_async_update_many_multiple_todos(self):
        """Test that async_update_many works like async_update_batch."""
        storage = FileStorage()

        # Add some todos first
        todos = [
            Todo(title="Async Task 1"),
            Todo(title="Async Task 2"),
        ]
        added = await storage.async_add_many(todos)

        # Update them
        updated_todos = [
            Todo(id=added[0].id, title="Updated Async Task 1"),
            Todo(id=added[1].id, title="Updated Async Task 2"),
        ]
        result = await storage.async_update_many(updated_todos)

        assert len(result) == 2
        assert all(isinstance(todo, Todo) for todo in result)
        assert [todo.title for todo in result] == ["Updated Async Task 1", "Updated Async Task 2"]

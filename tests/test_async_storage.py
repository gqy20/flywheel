"""Test asynchronous storage operations."""

import asyncio
import pytest
from pathlib import Path

from flywheel.storage import FileStorage
from flywheel.todo import Todo


class TestAsyncStorage:
    """Test async methods in FileStorage."""

    @pytest.fixture
    def temp_storage_path(self, tmp_path):
        """Create a temporary storage path."""
        return tmp_path / "test_todos.json"

    @pytest.fixture
    def storage(self, temp_storage_path):
        """Create a FileStorage instance for testing."""
        storage = FileStorage(str(temp_storage_path))
        yield storage
        # Cleanup
        if Path(temp_storage_path).exists():
            Path(temp_storage_path).unlink()

    @pytest.mark.asyncio
    async def test_async_add_todo(self, storage):
        """Test async_add method adds a todo successfully."""
        todo = Todo(title="Async Test Todo", status="pending")

        # This test will fail until async_add is implemented
        result = await storage.async_add(todo)

        assert result is not None
        assert result.title == "Async Test Todo"
        assert result.status == "pending"
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_async_list_todos(self, storage):
        """Test async_list method retrieves all todos."""
        # First add a todo
        todo1 = Todo(title="Todo 1", status="pending")
        await storage.async_add(todo1)

        todo2 = Todo(title="Todo 2", status="completed")
        await storage.async_add(todo2)

        # This test will fail until async_list is implemented
        todos = await storage.async_list()

        assert len(todos) == 2
        assert any(t.title == "Todo 1" for t in todos)
        assert any(t.title == "Todo 2" for t in todos)

    @pytest.mark.asyncio
    async def test_async_list_with_status_filter(self, storage):
        """Test async_list with status filtering."""
        todo1 = Todo(title="Pending Todo", status="pending")
        await storage.async_add(todo1)

        todo2 = Todo(title="Completed Todo", status="completed")
        await storage.async_add(todo2)

        pending_todos = await storage.async_list(status="pending")

        assert len(pending_todos) == 1
        assert pending_todos[0].title == "Pending Todo"
        assert pending_todos[0].status == "pending"

    @pytest.mark.asyncio
    async def test_async_get_todo(self, storage):
        """Test async_get method retrieves a specific todo."""
        todo = Todo(title="Get Me", status="pending")
        added = await storage.async_add(todo)

        # This test will fail until async_get is implemented
        retrieved = await storage.async_get(added.id)

        assert retrieved is not None
        assert retrieved.id == added.id
        assert retrieved.title == "Get Me"

    @pytest.mark.asyncio
    async def test_async_get_nonexistent_todo(self, storage):
        """Test async_get with a non-existent todo ID."""
        # This test will fail until async_get is implemented
        result = await storage.async_get(99999)

        assert result is None

    @pytest.mark.asyncio
    async def test_async_update_todo(self, storage):
        """Test async_update method updates a todo."""
        todo = Todo(title="Original Title", status="pending")
        added = await storage.async_add(todo)

        # Update the todo
        updated_todo = Todo(id=added.id, title="Updated Title", status="completed")

        # This test will fail until async_update is implemented
        result = await storage.async_update(updated_todo)

        assert result is not None
        assert result.title == "Updated Title"
        assert result.status == "completed"

        # Verify the update persisted
        retrieved = await storage.async_get(added.id)
        assert retrieved.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_async_delete_todo(self, storage):
        """Test async_delete method removes a todo."""
        todo = Todo(title="Delete Me", status="pending")
        added = await storage.async_add(todo)

        # This test will fail until async_delete is implemented
        result = await storage.async_delete(added.id)

        assert result is True

        # Verify the todo was deleted
        retrieved = await storage.async_get(added.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_async_delete_nonexistent_todo(self, storage):
        """Test async_delete with a non-existent todo ID."""
        # This test will fail until async_delete is implemented
        result = await storage.async_delete(99999)

        assert result is False

    @pytest.mark.asyncio
    async def test_async_concurrent_operations(self, storage):
        """Test that multiple async operations can run concurrently."""
        todos = [
            Todo(title=f"Concurrent Todo {i}", status="pending")
            for i in range(10)
        ]

        # This test will fail until async_add is implemented
        tasks = [storage.async_add(todo) for todo in todos]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r is not None for r in results)

        # Verify all todos were added
        all_todos = await storage.async_list()
        assert len(all_todos) == 10

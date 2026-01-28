"""Test for issue #811 - Async batch methods should exist in AbstractStorage.

This test verifies that the AbstractStorage class has async batch methods
(async_add_batch, async_update_batch) that match the synchronous versions.
"""

import asyncio
import pytest
from pathlib import Path

from flywheel.storage import AbstractStorage, FileStorage
from flywheel.todo import Todo


class TestAbstractStorageHasAsyncBatchMethods:
    """Test that AbstractStorage defines async batch methods."""

    def test_abstract_storage_has_async_add_batch(self):
        """AbstractStorage should have async_add_batch abstract method."""
        # Check that the method exists and is abstract
        assert hasattr(AbstractStorage, 'async_add_batch')
        # Verify it's an abstract method
        import inspect
        method = getattr(AbstractStorage, 'async_add_batch')
        assert inspect.iscoroutinefunction(method), "async_add_batch should be a coroutine"

    def test_abstract_storage_has_async_update_batch(self):
        """AbstractStorage should have async_update_batch abstract method."""
        # Check that the method exists
        assert hasattr(AbstractStorage, 'async_update_batch')
        # Verify it's an abstract method
        import inspect
        method = getattr(AbstractStorage, 'async_update_batch')
        assert inspect.iscoroutinefunction(method), "async_update_batch should be a coroutine"


class TestFileStorageImplementsAsyncBatchMethods:
    """Test that FileStorage implements async batch methods."""

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
    async def test_async_add_batch(self, storage):
        """Test async_add_batch method adds multiple todos."""
        todos = [
            Todo(title=f"Batch Todo {i}", status="pending")
            for i in range(5)
        ]

        # This test will fail until async_add_batch is implemented
        results = await storage.async_add_batch(todos)

        assert len(results) == 5
        assert all(r.id is not None for r in results)
        assert all(r.title == f"Batch Todo {i}" for i, r in enumerate(results))

    @pytest.mark.asyncio
    async def test_async_update_batch(self, storage):
        """Test async_update_batch method updates multiple todos."""
        # First add some todos
        todos = [
            Todo(title=f"Original {i}", status="pending")
            for i in range(3)
        ]
        added = await storage.async_add_batch(todos)

        # Update them
        updated_todos = [
            Todo(id=t.id, title=f"Updated {i}", status="completed")
            for i, t in enumerate(added)
        ]

        # This test will fail until async_update_batch is implemented
        results = await storage.async_update_batch(updated_todos)

        assert len(results) == 3
        assert all(r.title.startswith("Updated") for r in results)
        assert all(r.status == "completed" for r in results)

    @pytest.mark.asyncio
    async def test_async_batch_operations_are_more_efficient(self, storage):
        """Test that batch operations work correctly (regression test)."""
        # Add a batch of todos
        todos = [Todo(title=f"Todo {i}", status="pending") for i in range(10)]
        results = await storage.async_add_batch(todos)

        # Verify all were added
        all_todos = await storage.async_list()
        assert len(all_todos) == 10

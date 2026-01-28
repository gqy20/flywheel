"""Tests for Issue #878 - bulk_update method."""

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo, Status


def test_bulk_update_returns_count():
    """Test that bulk_update returns the count of updated todos."""
    storage = FileStorage()

    # Add initial todos
    todo1 = storage.add(Todo(id=None, title="Task 1"))
    todo2 = storage.add(Todo(id=None, title="Task 2"))
    todo3 = storage.add(Todo(id=None, title="Task 3"))

    # Update multiple todos
    todo1.status = Status.DONE
    todo2.status = Status.DONE
    todo3.status = Status.DONE

    # Call bulk_update and verify it returns count
    count = storage.bulk_update([todo1, todo2, todo3])
    assert count == 3


def test_bulk_update_empty_list():
    """Test that bulk_update with empty list returns 0."""
    storage = FileStorage()
    count = storage.bulk_update([])
    assert count == 0


def test_bulk_update_partially_existing_todos():
    """Test that bulk_update only counts actually updated todos."""
    storage = FileStorage()

    # Add one todo
    todo1 = storage.add(Todo(id=None, title="Task 1"))

    # Create a todo that doesn't exist (id=999)
    todo_nonexistent = Todo(id=999, title="Non-existent")

    # Mark the existing todo as done
    todo1.status = Status.DONE

    # bulk_update should only update the existing todo
    count = storage.bulk_update([todo1, todo_nonexistent])
    assert count == 1


def test_bulk_update_actually_updates():
    """Test that bulk_update actually updates the todos in storage."""
    storage = FileStorage()

    # Add initial todos
    todo1 = storage.add(Todo(id=None, title="Task 1"))
    todo2 = storage.add(Todo(id=None, title="Task 2"))

    # Update todos
    todo1.status = Status.DONE
    todo2.status = Status.IN_PROGRESS

    # Call bulk_update
    storage.bulk_update([todo1, todo2])

    # Verify updates persisted
    retrieved1 = storage.get(todo1.id)
    retrieved2 = storage.get(todo2.id)

    assert retrieved1.status == Status.DONE
    assert retrieved2.status == Status.IN_PROGRESS


@pytest.mark.asyncio
async def test_async_bulk_update_returns_count():
    """Test that async_bulk_update returns the count of updated todos."""
    storage = FileStorage()

    # Add initial todos
    todo1 = await storage.async_add(Todo(id=None, title="Task 1"))
    todo2 = await storage.async_add(Todo(id=None, title="Task 2"))
    todo3 = await storage.async_add(Todo(id=None, title="Task 3"))

    # Update multiple todos
    todo1.status = Status.DONE
    todo2.status = Status.DONE
    todo3.status = Status.DONE

    # Call async_bulk_update and verify it returns count
    count = await storage.async_bulk_update([todo1, todo2, todo3])
    assert count == 3


@pytest.mark.asyncio
async def test_async_bulk_update_empty_list():
    """Test that async_bulk_update with empty list returns 0."""
    storage = FileStorage()
    count = await storage.async_bulk_update([])
    assert count == 0


@pytest.mark.asyncio
async def test_async_bulk_update_actually_updates():
    """Test that async_bulk_update actually updates the todos in storage."""
    storage = FileStorage()

    # Add initial todos
    todo1 = await storage.async_add(Todo(id=None, title="Task 1"))
    todo2 = await storage.async_add(Todo(id=None, title="Task 2"))

    # Update todos
    todo1.status = Status.DONE
    todo2.status = Status.IN_PROGRESS

    # Call async_bulk_update
    await storage.async_bulk_update([todo1, todo2])

    # Verify updates persisted
    retrieved1 = await storage.async_get(todo1.id)
    retrieved2 = await storage.async_get(todo2.id)

    assert retrieved1.status == Status.DONE
    assert retrieved2.status == Status.IN_PROGRESS

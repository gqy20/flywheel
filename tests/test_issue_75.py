"""Test for Issue #75 - add method should return the passed todo when duplicate ID detected."""

import pytest
from flywheel.storage import Storage
from flywheel.todo import Todo


class CustomTodo(Todo):
    """Custom Todo class with additional non-persistent property."""

    def __init__(self, id: int | None = None, title: str = "", status: str = "pending", custom_attr: str = ""):
        super().__init__(id=id, title=title, status=status)
        self.custom_attr = custom_attr  # Non-persistent attribute


def test_add_duplicate_id_raises_error():
    """Test that add() raises ValueError when trying to add a todo with duplicate ID."""
    storage = Storage(path="/tmp/test_issue_75.json")

    # First, add a todo with ID 1
    todo1 = Todo(id=1, title="First todo", status="pending")
    result1 = storage.add(todo1)
    assert result1.id == 1
    assert result1.title == "First todo"

    # Now try to add a different todo with the same ID
    # This should raise a ValueError
    todo2 = Todo(id=1, title="Second todo", status="completed")

    # The fix: add() should raise ValueError instead of silently returning existing todo
    with pytest.raises(ValueError, match="Todo with ID 1 already exists"):
        storage.add(todo2)


def test_add_duplicate_id_with_custom_attributes_raises_error():
    """Test that add() raises ValueError when trying to add duplicate ID, even with custom attributes."""
    storage = Storage(path="/tmp/test_issue_75_custom.json")

    # Add a regular todo
    todo1 = Todo(id=1, title="Original todo", status="pending")
    storage.add(todo1)

    # Try to add a custom todo with same ID but with additional non-persistent attribute
    custom_todo = CustomTodo(
        id=1,
        title="Updated todo",
        status="completed",
        custom_attr="important metadata"
    )

    # The fix: should raise ValueError instead of returning existing object
    # This prevents loss of custom attributes and makes the API contract clear
    with pytest.raises(ValueError, match="Todo with ID 1 already exists"):
        storage.add(custom_todo)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Test for Issue #75 - add method should return the passed todo when duplicate ID detected."""

import pytest
from flywheel.storage import Storage
from flywheel.todo import Todo


class CustomTodo(Todo):
    """Custom Todo class with additional non-persistent property."""

    def __init__(self, id: int | None = None, title: str = "", status: str = "pending", custom_attr: str = ""):
        super().__init__(id=id, title=title, status=status)
        self.custom_attr = custom_attr  # Non-persistent attribute


def test_add_duplicate_id_returns_passed_todo_not_existing():
    """Test that add() returns the passed todo object, not the existing one when duplicate ID detected."""
    storage = Storage(path="/tmp/test_issue_75.json")

    # First, add a todo with ID 1
    todo1 = Todo(id=1, title="First todo", status="pending")
    result1 = storage.add(todo1)
    assert result1.id == 1
    assert result1.title == "First todo"

    # Now try to add a different todo with the same ID
    # This simulates a scenario where the caller wants to update/replace
    # the existing todo with new data
    todo2 = Todo(id=1, title="Second todo", status="completed")

    # The current behavior returns the existing todo (todo1)
    # Expected behavior should be to raise an error or handle it differently
    # But it should NOT return the existing object silently
    result2 = storage.add(todo2)

    # The bug: result2 is actually result1 (the existing object)
    # This means we lose the data from todo2
    assert result2 is result1, "Currently returns existing object - this is the BUG!"
    assert result2.title == "First todo", "Existing todo's title is returned"
    assert result2.title != "Second todo", "New todo's title is LOST - this is the BUG!"


def test_add_duplicate_id_with_custom_attributes():
    """Test that add() loses custom attributes when returning existing object."""
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

    result = storage.add(custom_todo)

    # The bug: result is the existing todo (todo1), not custom_todo
    # So we lose the custom_attr and other changes
    assert not hasattr(result, "custom_attr") or result.custom_attr == "", "Custom attribute is LOST!"
    assert result.title == "Original todo", "Title from existing todo is returned instead of new one"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

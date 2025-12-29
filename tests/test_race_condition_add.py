"""Test for race condition in add method - Issue #53."""

import pytest
from flywheel.storage import Storage
from flywheel.todo import Todo


def test_add_with_external_id_should_check_duplicate_first():
    """
    Test that add method checks for duplicate IDs BEFORE any other logic.

    The race condition occurs when:
    1. A todo with an externally set ID is passed
    2. The duplicate check happens AFTER ID generation block
    3. This allows the same todo to be added multiple times

    Expected behavior:
    - The duplicate check should happen at the beginning of the method
    - If the ID exists, return the existing todo immediately
    """
    storage = Storage(path="/tmp/test_race_condition.json")

    # Clear any existing todos
    for todo in storage.list():
        storage.delete(todo.id)

    # Add a todo with auto-generated ID
    todo1 = Todo(id=None, title="First todo", status="pending")
    added1 = storage.add(todo1)

    # Try to add a todo with the same ID externally set
    # This should return the existing todo, not add a duplicate
    todo2 = Todo(id=added1.id, title="Second todo", status="pending")
    result = storage.add(todo2)

    # Verify that the existing todo was returned
    assert result.id == added1.id
    assert result.title == "First todo"  # Should be the original todo
    assert result.status == "pending"

    # Verify that only one todo exists
    todos = storage.list()
    assert len(todos) == 1
    assert todos[0].id == added1.id
    assert todos[0].title == "First todo"

    # Cleanup
    import os
    if os.path.exists("/tmp/test_race_condition.json"):
        os.remove("/tmp/test_race_condition.json")


def test_add_with_nonexistent_external_id():
    """
    Test that add method works correctly when ID doesn't exist yet.

    This is the positive case - adding with an external ID that doesn't exist
    should work fine.
    """
    storage = Storage(path="/tmp/test_race_condition_external.json")

    # Clear any existing todos
    for todo in storage.list():
        storage.delete(todo.id)

    # Add a todo with an external ID that doesn't exist
    todo = Todo(id=999, title="Todo with external ID", status="pending")
    result = storage.add(todo)

    # Verify it was added
    assert result.id == 999
    assert result.title == "Todo with external ID"

    # Try to add another todo with the same ID
    # This should return the existing todo
    todo2 = Todo(id=999, title="Duplicate todo", status="pending")
    result2 = storage.add(todo2)

    # Should return the existing todo
    assert result2.id == 999
    assert result2.title == "Todo with external ID"

    # Verify only one todo exists
    todos = storage.list()
    assert len(todos) == 1

    # Cleanup
    import os
    if os.path.exists("/tmp/test_race_condition_external.json"):
        os.remove("/tmp/test_race_condition_external.json")

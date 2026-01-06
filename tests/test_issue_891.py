"""Test for issue #891: Potential loss of 'created_at' data during deserialization."""

import time
from datetime import datetime

from flywheel.todo import Todo


def test_created_at_preserved_when_none():
    """Test that created_at=None is preserved during deserialization.

    When a Todo is created with created_at=None, serialized, and then
    deserialized, the created_at field should remain None, not be replaced
    by the default_factory value (current time).
    """
    # Create a todo with created_at explicitly set to None
    original_todo = Todo(
        id=1,
        title="Test Todo",
        created_at=None
    )

    # Verify initial state
    assert original_todo.created_at is None

    # Serialize to dict
    todo_dict = original_todo.to_dict()

    # Verify dict representation has None
    assert todo_dict["created_at"] is None

    # Small delay to ensure default_factory would produce different time
    time.sleep(0.01)

    # Deserialize from dict
    restored_todo = Todo.from_dict(todo_dict)

    # The bug: created_at would be set to current time by default_factory
    # instead of preserving None
    assert restored_todo.created_at is None, (
        f"created_at should be None but got {restored_todo.created_at}. "
        "This indicates the default_factory overwrote the original None value."
    )


def test_created_at_preserved_with_value():
    """Test that created_at value is preserved during deserialization."""
    # Create a todo with a specific created_at timestamp
    original_timestamp = "2024-01-01T12:00:00.123456"

    original_todo = Todo(
        id=1,
        title="Test Todo",
        created_at=original_timestamp
    )

    # Verify initial state
    assert original_todo.created_at == original_timestamp

    # Serialize to dict
    todo_dict = original_todo.to_dict()

    # Verify dict representation has the timestamp
    assert todo_dict["created_at"] == original_timestamp

    # Deserialize from dict
    restored_todo = Todo.from_dict(todo_dict)

    # The timestamp should be preserved
    assert restored_todo.created_at == original_timestamp, (
        f"created_at should be {original_timestamp} but got {restored_todo.created_at}"
    )


def test_created_at_round_trip():
    """Test that created_at survives round-trip serialization/deserialization."""
    # Test with None value
    todo_none = Todo(id=1, title="Test", created_at=None)
    assert Todo.from_dict(todo_none.to_dict()).created_at is None

    # Test with actual timestamp
    timestamp = "2024-03-15T08:30:45.987654"
    todo_with_time = Todo(id=2, title="Test", created_at=timestamp)
    assert Todo.from_dict(todo_with_time.to_dict()).created_at == timestamp

    # Test with default_factory value (should not be overwritten)
    todo_default = Todo(id=3, title="Test")
    original_created_at = todo_default.created_at
    restored_todo = Todo.from_dict(todo_default.to_dict())
    assert restored_todo.created_at == original_created_at

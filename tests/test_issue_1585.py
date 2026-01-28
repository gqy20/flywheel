"""Test for issue #1585 - created_at should be unique per instance."""

import time
from dataclasses import dataclass, field
from datetime import datetime

import pytest

from flywheel.todo import Todo


def test_created_at_unique_per_instance():
    """Test that each Todo instance gets a unique created_at timestamp.

    This test verifies the fix for issue #1585 where the default_factory
    lambda was being executed at class definition time instead of instance
    creation time, causing all instances to share the same timestamp.
    """
    # Create two Todo instances without specifying created_at
    todo1 = Todo(id=None, title="Todo 1")
    # Small delay to ensure different timestamps
    time.sleep(0.01)
    todo2 = Todo(id=None, title="Todo 2")

    # Both should have created_at set
    assert todo1.created_at is not None, "First todo should have created_at"
    assert todo2.created_at is not None, "Second todo should have created_at"

    # They should have different timestamps (not the same value from class definition)
    assert todo1.created_at != todo2.created_at, (
        f"created_at timestamps should be unique per instance. "
        f"Got todo1.created_at={todo1.created_at}, todo2.created_at={todo2.created_at}"
    )

    # Verify both are valid ISO format timestamps
    datetime.fromisoformat(todo1.created_at)
    datetime.fromisoformat(todo2.created_at)


def test_created_at_can_be_overridden():
    """Test that created_at can still be explicitly set."""
    custom_time = "2025-01-13T12:00:00"
    todo = Todo(id=None, title="Todo", created_at=custom_time)

    assert todo.created_at == custom_time


def test_created_at_none_when_explicitly_set():
    """Test that created_at can be explicitly set to None."""
    todo = Todo(id=None, title="Todo", created_at=None)

    assert todo.created_at is None

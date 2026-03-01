"""Tests for Todo.age property (Issue #6453).

These tests verify that:
1. todo.age returns a datetime.timedelta object
2. age is positive for past creation times
3. age is accurate within 1 second of actual elapsed time
4. age for newly created todo is near zero
"""

from __future__ import annotations

import time
from datetime import timedelta

from flywheel.todo import Todo


def test_todo_age_returns_timedelta() -> None:
    """Todo.age should return a datetime.timedelta object."""
    todo = Todo(id=1, text="test task")
    result = todo.age

    assert isinstance(result, timedelta), f"Expected timedelta, got {type(result)}"


def test_todo_age_positive_for_past_creation() -> None:
    """Todo.age should be positive for todos created in the past."""
    todo = Todo(id=1, text="test task")
    # Small delay to ensure positive age
    time.sleep(0.01)
    result = todo.age

    assert result > timedelta(0), f"Expected positive age, got {result}"


def test_todo_age_increases_over_time() -> None:
    """Todo.age should increase as time passes."""
    todo = Todo(id=1, text="test task")
    initial_age = todo.age

    # Wait a small amount of time
    time.sleep(0.1)

    later_age = todo.age
    assert later_age > initial_age, (
        f"Age should increase over time: initial={initial_age}, later={later_age}"
    )


def test_todo_age_newly_created_near_zero() -> None:
    """Todo.age for a newly created todo should be near zero."""
    todo = Todo(id=1, text="test task")
    result = todo.age

    # Age should be less than 1 second for a newly created todo
    assert result < timedelta(seconds=1), (
        f"Age for new todo should be < 1s, got {result}"
    )


def test_todo_age_with_explicit_created_at() -> None:
    """Todo.age should work correctly when created_at is explicitly set."""
    # Create a todo with a created_at from 5 seconds ago
    from datetime import UTC, datetime

    past_time = datetime.now(UTC) - timedelta(seconds=5)
    todo = Todo(
        id=1, text="old task", created_at=past_time.isoformat()
    )

    result = todo.age

    # Age should be at least 5 seconds (allowing some tolerance)
    assert result >= timedelta(seconds=4.5), (
        f"Expected age >= 4.5s for todo created 5s ago, got {result}"
    )
    assert result < timedelta(seconds=10), (
        f"Expected age < 10s, got {result}"
    )

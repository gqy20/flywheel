"""Tests for Todo.age property (Issue #6453).

These tests verify that:
1. todo.age returns a datetime.timedelta object
2. age is positive for past creation times
3. age is accurate within 1 second of actual elapsed time
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
    # Create a todo with a created_at timestamp in the past
    past_timestamp = "2024-01-01T00:00:00+00:00"
    todo = Todo(id=1, text="old task", created_at=past_timestamp)

    age = todo.age

    # Age should be positive (the todo was created in the past)
    assert age > timedelta(0), f"Expected positive age for past creation, got {age}"


def test_todo_age_near_zero_for_new_todo() -> None:
    """Todo.age should be near zero for a newly created todo."""
    todo = Todo(id=1, text="new task")
    age = todo.age

    # Age should be less than 1 second for a newly created todo
    assert age < timedelta(seconds=1), (
        f"Expected age < 1s for new todo, got {age.total_seconds()}s"
    )


def test_todo_age_increases_over_time() -> None:
    """Todo.age should increase over time (with small sleep)."""
    todo = Todo(id=1, text="test task")
    initial_age = todo.age

    # Sleep a short time
    time.sleep(0.1)

    later_age = todo.age

    # Age should have increased
    assert later_age > initial_age, (
        f"Expected age to increase, initial={initial_age}, later={later_age}"
    )

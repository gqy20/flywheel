"""Regression test for issue #6453: Add age property to show time since creation."""

import time
from datetime import UTC, datetime, timedelta

from flywheel.todo import Todo


class TestTodoAgeProperty:
    """Tests for the Todo.age property (issue #6453)."""

    def test_age_returns_timedelta(self) -> None:
        """Test that age property returns a datetime.timedelta object."""
        todo = Todo(id=1, text="Test todo")
        age = todo.age
        assert isinstance(age, timedelta), f"Expected timedelta, got {type(age)}"

    def test_age_is_positive_for_past_creation(self) -> None:
        """Test that age is positive for past creation times."""
        # Create a todo with a created_at timestamp in the past
        past_time = datetime.now(UTC) - timedelta(hours=2)
        todo = Todo(
            id=1,
            text="Old todo",
            created_at=past_time.isoformat(),
        )
        age = todo.age
        assert age > timedelta(0), f"Expected positive age, got {age}"
        # Age should be at least 2 hours (with small margin for execution time)
        assert age >= timedelta(hours=2) - timedelta(seconds=1), (
            f"Expected age >= 2 hours, got {age}"
        )

    def test_age_for_newly_created_todo_is_near_zero(self) -> None:
        """Test that age for newly created todo is near zero."""
        todo = Todo(id=1, text="New todo")
        age = todo.age
        # Age should be less than 1 second for a newly created todo
        assert age < timedelta(seconds=1), (
            f"Expected age < 1 second for new todo, got {age}"
        )

    def test_age_increases_over_time(self) -> None:
        """Test that age increases over time (with small sleep)."""
        todo = Todo(id=1, text="Test todo")
        initial_age = todo.age

        # Sleep for a short time
        time.sleep(0.1)

        later_age = todo.age
        assert later_age > initial_age, (
            f"Expected age to increase, initial={initial_age}, later={later_age}"
        )

    def test_age_is_accurate_within_one_second(self) -> None:
        """Test that age is accurate within 1 second of actual elapsed time."""
        # Create a todo with a known creation time
        creation_time = datetime.now(UTC)
        todo = Todo(
            id=1,
            text="Test todo",
            created_at=creation_time.isoformat(),
        )

        # Wait a short time
        elapsed_seconds = 0.5
        time.sleep(elapsed_seconds)

        age = todo.age
        expected_min = timedelta(seconds=elapsed_seconds - 0.1)  # Small margin
        expected_max = timedelta(seconds=elapsed_seconds + 0.5)  # Allow more margin

        assert expected_min <= age <= expected_max, (
            f"Expected age between {expected_min} and {expected_max}, got {age}"
        )

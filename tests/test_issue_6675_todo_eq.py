"""Tests for Todo.__eq__ method (Issue #6675).

These tests verify that:
1. Todo objects can be compared for equality
2. Equality compares id, text, and done fields
3. Timestamps (created_at, updated_at) are ignored for equality
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_identical_todos() -> None:
    """Todo(id=1, text='a') == Todo(id=1, text='a') should return True."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=False)
    assert todo1 == todo2


def test_todo_eq_different_ids() -> None:
    """Todo(id=1, text='a') == Todo(id=2, text='a') should return False."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=2, text="a", done=False)
    assert todo1 != todo2


def test_todo_eq_different_text() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=False)
    assert todo1 != todo2


def test_todo_eq_done_status_affects_equality() -> None:
    """Done status should affect equality."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)
    assert todo1 != todo2


def test_todo_eq_ignores_timestamps() -> None:
    """Equality should ignore created_at and updated_at fields."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00", updated_at="2024-01-01T00:00:00")
    todo2 = Todo(id=1, text="a", done=False, created_at="2024-12-31T23:59:59", updated_at="2024-12-31T23:59:59")
    assert todo1 == todo2


def test_todo_eq_with_non_todo() -> None:
    """Comparing Todo with a non-Todo should return False."""
    todo = Todo(id=1, text="a", done=False)
    assert todo != "not a todo"
    assert todo != 1
    assert todo is not None
    assert todo != {"id": 1, "text": "a", "done": False}


def test_todo_eq_reflexive() -> None:
    """A todo should equal itself (reflexivity)."""
    todo = Todo(id=1, text="a", done=False)
    assert todo == todo


def test_todo_eq_symmetric() -> None:
    """Equality should be symmetric: a == b implies b == a."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=False)
    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_transitive() -> None:
    """Equality should be transitive: a == b and b == c implies a == c."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=False)
    todo3 = Todo(id=1, text="a", done=False)
    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3


def test_todo_eq_in_list() -> None:
    """Todo objects should be comparable in lists/collections."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=False)
    assert todo1 in [todo2, Todo(id=2, text="b")]


def test_todo_eq_with_minimal_fields() -> None:
    """Equality should work with only required fields specified."""
    todo1 = Todo(id=42, text="task")
    todo2 = Todo(id=42, text="task")
    assert todo1 == todo2

"""Tests for Todo.__eq__ method (Issue #3059).

These tests verify that:
1. Todo objects with same id, text, done compare as equal
2. Todo objects with different fields compare as not equal
3. Equality works for list membership tests and deduplication
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Todo objects with identical id, text, done should be equal."""
    t1 = Todo(id=1, text="buy milk", done=False, created_at="", updated_at="")
    t2 = Todo(id=1, text="buy milk", done=False, created_at="", updated_at="")
    assert t1 == t2


def test_todo_equality_different_id() -> None:
    """Todo objects with different id should not be equal."""
    t1 = Todo(id=1, text="buy milk", done=False)
    t2 = Todo(id=2, text="buy milk", done=False)
    assert t1 != t2


def test_todo_equality_different_text() -> None:
    """Todo objects with different text should not be equal."""
    t1 = Todo(id=1, text="buy milk", done=False)
    t2 = Todo(id=1, text="buy bread", done=False)
    assert t1 != t2


def test_todo_equality_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    t1 = Todo(id=1, text="buy milk", done=False)
    t2 = Todo(id=1, text="buy milk", done=True)
    assert t1 != t2


def test_todo_equality_ignores_timestamps() -> None:
    """Equality should ignore created_at and updated_at timestamps."""
    t1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    t2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31", updated_at="2024-12-31")
    assert t1 == t2


def test_todo_list_membership() -> None:
    """Equality enables proper list membership tests."""
    t1 = Todo(id=1, text="buy milk", done=False)
    t2 = Todo(id=1, text="buy milk", done=False)  # Same values, different object
    todo_list = [t1]
    assert t2 in todo_list


def test_todo_deduplication() -> None:
    """Equality enables deduplication using list comprehension."""
    t1 = Todo(id=1, text="buy milk", done=False)
    t2 = Todo(id=1, text="buy milk", done=False)  # Duplicate
    t3 = Todo(id=2, text="buy bread", done=False)  # Unique

    # Deduplicate using list comprehension (relies on __eq__)
    todo_list = [t1, t2, t3]
    unique_todos = []
    for todo in todo_list:
        if todo not in unique_todos:
            unique_todos.append(todo)

    assert len(unique_todos) == 2

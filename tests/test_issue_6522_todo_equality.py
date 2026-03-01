"""Tests for Todo.__eq__ method (Issue #6522).

These tests verify that:
1. Todo objects with same id, text, done are equal
2. Todo objects with different id, text, or done are not equal
3. Comparison with non-Todo returns NotImplemented/False
4. Timestamps are excluded from equality comparison
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Todo objects with same id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_equality_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_equality_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_equality_with_none() -> None:
    """Comparing Todo with None should return False."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != None  # noqa: E711


def test_todo_equality_with_non_todo() -> None:
    """Comparing Todo with non-Todo type should return False."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}


def test_todo_equality_excludes_timestamps() -> None:
    """Equality should exclude timestamps - todos with same id/text/done but different timestamps should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo1.created_at = "2024-01-01T00:00:00+00:00"
    todo1.updated_at = "2024-01-01T00:00:00+00:00"

    todo2 = Todo(id=1, text="buy milk", done=False)
    todo2.created_at = "2024-12-31T23:59:59+00:00"
    todo2.updated_at = "2024-12-31T23:59:59+00:00"

    # Should be equal despite different timestamps
    assert todo1 == todo2


def test_todo_equality_reflexive() -> None:
    """A todo should equal itself (reflexivity)."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo == todo


def test_todo_equality_symmetric() -> None:
    """Equality should be symmetric: if a == b then b == a."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_equality_transitive() -> None:
    """Equality should be transitive: if a == b and b == c then a == c."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    todo3 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3

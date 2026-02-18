"""Tests for Todo.__eq__ method (Issue #4175).

These tests verify that:
1. Todo objects with same id, text, done are equal
2. Todo objects with different id, text, or done are not equal
3. Timestamps are excluded from equality comparison (pragmatic equality)
"""

from __future__ import annotations

import contextlib

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Todo(1, 'a') == Todo(1, 'a') should return True."""
    todo1 = Todo(id=1, text="test", done=False)
    todo2 = Todo(id=1, text="test", done=False)
    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Todo(1, 'a') != Todo(2, 'a') should return True."""
    todo1 = Todo(id=1, text="test", done=False)
    todo2 = Todo(id=2, text="test", done=False)
    assert todo1 != todo2


def test_todo_equality_different_done() -> None:
    """Todo(1, 'a', done=True) != Todo(1, 'a', done=False) should return True."""
    todo1 = Todo(id=1, text="test", done=True)
    todo2 = Todo(id=1, text="test", done=False)
    assert todo1 != todo2


def test_todo_equality_different_text() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task b", done=False)
    assert todo1 != todo2


def test_todo_equality_ignores_timestamps() -> None:
    """Equality should ignore created_at and updated_at fields."""
    todo1 = Todo(id=1, text="test", done=False, created_at="2024-01-01T00:00:00")
    todo2 = Todo(id=1, text="test", done=False, created_at="2024-12-31T23:59:59")
    assert todo1 == todo2


def test_todo_equality_with_non_todo() -> None:
    """Comparing Todo with non-Todo should return False."""
    todo = Todo(id=1, text="test", done=False)
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "test", "done": False}
    assert todo is not None


def test_todo_equality_reflexive() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="test", done=False)
    assert todo == todo


def test_todo_equality_symmetric() -> None:
    """If a == b, then b == a."""
    todo1 = Todo(id=1, text="test", done=False)
    todo2 = Todo(id=1, text="test", done=False)
    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_equality_transitive() -> None:
    """If a == b and b == c, then a == c."""
    todo1 = Todo(id=1, text="test", done=False)
    todo2 = Todo(id=1, text="test", done=False)
    todo3 = Todo(id=1, text="test", done=False)
    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3


def test_todo_hash_consistency() -> None:
    """Equal Todo objects should hash the same (if hashable)."""
    todo1 = Todo(id=1, text="test", done=False)
    todo2 = Todo(id=1, text="test", done=False)
    # If Todo becomes hashable, equal objects should have equal hashes
    with contextlib.suppress(TypeError):
        assert hash(todo1) == hash(todo2)

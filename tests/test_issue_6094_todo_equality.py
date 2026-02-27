"""Tests for Todo.__eq__ method (Issue #6094).

These tests verify that:
1. Todo objects are equal when id, text, and done fields match
2. Timestamps (created_at, updated_at) are excluded from equality comparison
3. Todo objects with different id/text/done are not equal
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id_text_done() -> None:
    """Two Todo objects with same id/text/done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_equality_different_timestamps() -> None:
    """Todo objects with same id/text/done but different timestamps should be equal."""
    # Create todos with explicit timestamps
    todo1 = Todo(
        id=1,
        text="buy milk",
        done=False,
        created_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-01T00:00:00+00:00",
    )
    todo2 = Todo(
        id=1,
        text="buy milk",
        done=False,
        created_at="2024-12-31T23:59:59+00:00",
        updated_at="2024-12-31T23:59:59+00:00",
    )

    # Should be equal despite different timestamps
    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_inequality_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_inequality_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_equality_with_non_todo() -> None:
    """Todo object should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "Todo(id=1, text='buy milk', done=False)"
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    assert todo != 1
    # Test against None using `is not` to satisfy PEP 8
    assert todo is not None


def test_todo_equality_reflexive() -> None:
    """A Todo object should be equal to itself."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo == todo


def test_todo_equality_symmetric() -> None:
    """Equality should be symmetric (a == b implies b == a)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_equality_transitive() -> None:
    """Equality should be transitive (a == b and b == c implies a == c)."""
    todo1 = Todo(
        id=1,
        text="buy milk",
        done=False,
        created_at="2024-01-01T00:00:00+00:00",
    )
    todo2 = Todo(
        id=1,
        text="buy milk",
        done=False,
        created_at="2024-06-01T00:00:00+00:00",
    )
    todo3 = Todo(
        id=1,
        text="buy milk",
        done=False,
        created_at="2024-12-31T23:59:59+00:00",
    )

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3


def test_todo_hash_consistency() -> None:
    """Equal Todo objects should have the same hash for use in sets/dicts."""
    todo1 = Todo(
        id=1,
        text="buy milk",
        done=False,
        created_at="2024-01-01T00:00:00+00:00",
    )
    todo2 = Todo(
        id=1,
        text="buy milk",
        done=False,
        created_at="2024-12-31T23:59:59+00:00",
    )

    # If __eq__ is defined, __hash__ should be consistent
    if todo1 == todo2:
        assert hash(todo1) == hash(todo2), (
            "Equal objects must have equal hashes for set/dict usage"
        )

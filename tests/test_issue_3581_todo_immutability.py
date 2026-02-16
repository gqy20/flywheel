"""Tests for Todo immutability/copy support (Issue #3581).

These tests verify that:
1. Todo objects can be compared for equality based on id/text/done
2. Todo objects are hashable based on id
3. Todo objects have a copy method to create derived instances
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id_text() -> None:
    """Todo(1, 'a') == Todo(1, 'a') should return True."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    assert todo1 == todo2


def test_todo_equality_same_id_text_done() -> None:
    """Todos with same id, text, and done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=True)
    todo2 = Todo(id=1, text="buy milk", done=True)
    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Todos with different id should not be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    assert todo1 != todo2


def test_todo_inequality_different_text() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    assert todo1 != todo2


def test_todo_inequality_different_done() -> None:
    """Todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)
    assert todo1 != todo2


def test_todo_hash_consistent() -> None:
    """hash(Todo(1, 'a')) should not throw exception and be consistent."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    assert hash(todo1) == hash(todo2)


def test_todo_hash_usable_in_set() -> None:
    """Todo objects should be usable in a set for deduplication."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    todo3 = Todo(id=2, text="b")

    todo_set = {todo1, todo2, todo3}
    # Since todo1 == todo2, set should have 2 items
    assert len(todo_set) == 2


def test_todo_hash_usable_in_dict() -> None:
    """Todo objects should be usable as dict keys."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")

    d = {todo1: "first"}
    d[todo2] = "second"

    # Since todo1 == todo2, dict should have 1 item
    assert len(d) == 1
    assert d[todo1] == "second"


def test_todo_copy_no_args() -> None:
    """copy() with no args should create an identical copy."""
    original = Todo(id=1, text="a", done=True)
    copied = original.copy()

    assert copied == original
    assert copied is not original


def test_todo_copy_with_text() -> None:
    """copy(text='new') should create a copy with new text."""
    original = Todo(id=1, text="a")
    copied = original.copy(text="b")

    assert copied.text == "b"
    assert copied.id == original.id
    assert copied.done == original.done


def test_todo_copy_with_done() -> None:
    """copy(done=True) should create a copy with new done status."""
    original = Todo(id=1, text="a", done=False)
    copied = original.copy(done=True)

    assert copied.done is True
    assert copied.id == original.id
    assert copied.text == original.text


def test_todo_copy_with_multiple_fields() -> None:
    """copy() should handle multiple field overrides."""
    original = Todo(id=1, text="a", done=False)
    copied = original.copy(text="b", done=True)

    assert copied.id == 1
    assert copied.text == "b"
    assert copied.done is True


def test_todo_copy_preserves_id() -> None:
    """copy() should preserve id by default."""
    original = Todo(id=42, text="task")
    copied = original.copy(text="new task")

    assert copied.id == 42


def test_todo_equality_ignores_timestamps() -> None:
    """Equality comparison should ignore created_at/updated_at fields."""
    todo1 = Todo(id=1, text="a", created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="a", created_at="2024-12-31", updated_at="2024-12-31")

    assert todo1 == todo2
    assert hash(todo1) == hash(todo2)

"""Tests for Issue #6056: __eq__ and __hash__ methods for proper equality comparison."""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id_and_text() -> None:
    """Issue #6056: Todo instances with same id and text should be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Issue #6056: Todo instances with different id should not be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    assert todo1 != todo2


def test_todo_equality_different_text() -> None:
    """Issue #6056: Todo instances with same id are equal regardless of text."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    # Same id means equal, regardless of text
    assert todo1 == todo2


def test_todo_hash_based_on_id() -> None:
    """Issue #6056: Todo instances with same id can be used in sets."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    # Same id should deduplicate in a set
    unique_todos = {todo1, todo2}
    assert len(unique_todos) == 1


def test_todo_hash_different_ids() -> None:
    """Issue #6056: Todo instances with different ids create multiple set entries."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    unique_todos = {todo1, todo2}
    assert len(unique_todos) == 2


def test_todo_can_be_used_as_dict_key() -> None:
    """Issue #6056: Todo instances can be used as dictionary keys."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    d = {todo1: "first"}
    # Same id should map to same key
    d[todo2] = "second"
    assert len(d) == 1
    assert d[todo1] == "second"


def test_todo_equality_ignores_timestamps() -> None:
    """Issue #6056: Equality should be based on id and text, not timestamps."""
    todo1 = Todo(id=1, text="a")
    todo1.created_at = "2024-01-01T00:00:00"
    todo1.updated_at = "2024-01-01T00:00:00"

    todo2 = Todo(id=1, text="a")
    todo2.created_at = "2024-12-31T23:59:59"
    todo2.updated_at = "2024-12-31T23:59:59"

    # Should be equal despite different timestamps
    assert todo1 == todo2


def test_todo_equality_ignores_done_state() -> None:
    """Issue #6056: Equality should be based on id and text, not done state."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)
    # Should be equal despite different done state
    assert todo1 == todo2


def test_todo_not_equal_to_non_todo() -> None:
    """Issue #6056: Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a")
    assert todo != 1
    assert todo != "a"
    assert todo != {"id": 1, "text": "a"}
    assert todo is not None

"""Tests for Todo.__eq__ and __hash__ methods (Issue #6056).

These tests verify that:
1. Todo objects with same id and text are equal
2. Todo objects can be used in sets (hashable)
3. Todo equality works regardless of done/created_at/updated_at status
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id_and_text() -> None:
    """Todo(id=1, text='a') == Todo(id=1, text='a') should return True."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    assert todo1 == todo2, "Todos with same id and text should be equal"


def test_todo_equality_different_id() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_equality_different_text() -> None:
    """Todos with same id but different text are still equal (id is the key)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    # Equality is based on id only, so same id = equal
    assert todo1 == todo2, "Todos with same id should be equal regardless of text"


def test_todo_hash_same_id_in_set() -> None:
    """Todo instances with same id can be used in sets and deduplicated."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    # Both have same id but different text - hash should be based on id
    # so they should be considered the same in a set
    todo_set = {todo1, todo2}
    # With hash based on id only, both would have same hash
    # but since __eq__ compares both id and text, they are NOT equal
    # So this test verifies that hash is based on id only
    assert len(todo_set) == 1, f"Expected 1 item in set (same id), got {len(todo_set)}"


def test_todo_hash_different_ids_in_set() -> None:
    """Todos with different ids should create separate set entries."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    todo_set = {todo1, todo2}
    assert len(todo_set) == 2, "Todos with different ids should be distinct in set"


def test_todo_equality_ignores_done_status() -> None:
    """Equality should only consider id and text, not done status."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)
    # Since hash is based on id only and __eq__ compares id + text,
    # these should be equal
    assert todo1 == todo2, "Todos with same id/text but different done should be equal"


def test_todo_hashable_for_dict_keys() -> None:
    """Todo instances can be used as dict keys."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id, different text

    todo_dict = {todo1: "value1"}
    # Since hash is based on id only, todo2 should map to same slot
    assert todo_dict[todo2] == "value1", "Same id should map to same dict entry"

"""Tests for Todo.__eq__ and __hash__ methods (Issue #4550).

These tests verify that:
1. Todos with same (id, text, done) are equal
2. Todos with different timestamps but same core fields are equal
3. hash() is based on id for stable hashing
4. Todos can be used in sets and dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_identity() -> None:
    """Two Todos with same (id, text, done) should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    assert todo1 == todo2


def test_todo_eq_different_id() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)
    assert todo1 != todo2


def test_todo_eq_different_text() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)
    assert todo1 != todo2


def test_todo_eq_different_done() -> None:
    """Todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)
    assert todo1 != todo2


def test_todo_eq_ignores_timestamps() -> None:
    """Todos with same core fields but different timestamps should be equal."""
    # Create two todos at different times (simulated by different created_at values)
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-02T00:00:00Z")
    assert todo1 == todo2, "Todos with same (id, text, done) should be equal regardless of timestamps"


def test_todo_hash_based_on_id() -> None:
    """hash(Todo) should be based on id for stable hashing."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)
    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_ids() -> None:
    """Todos with different ids should have different hashes."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)
    assert hash(todo1) != hash(todo2)


def test_todo_can_be_used_in_set() -> None:
    """Todos should be usable in a set without errors."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)  # Same as todo1
    todo3 = Todo(id=2, text="buy bread", done=False)

    todo_set = {todo1, todo2, todo3}
    # Set should deduplicate todos with same (id, text, done)
    assert len(todo_set) == 2, f"Expected 2 unique todos, got {len(todo_set)}"


def test_todo_can_be_used_as_dict_key() -> None:
    """Todos should be usable as dict keys without errors."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)  # Same as todo1

    d = {todo1: "first"}
    d[todo2] = "second"  # Should overwrite, not add new key

    assert len(d) == 1, f"Expected 1 key in dict, got {len(d)}"
    assert d[todo1] == "second"


def test_todo_eq_with_non_todo() -> None:
    """Comparing Todo with non-Todo should return False (not raise)."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo != "not a todo"
    assert todo != 1
    assert todo is not None
    assert todo != {"id": 1, "text": "buy milk", "done": False}

"""Tests for Todo equality and hash methods (Issue #3271)."""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id_different_text() -> None:
    """Todos with same id should be equal regardless of text."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_equality_same_id_different_done() -> None:
    """Todos with same id should be equal regardless of done status."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)

    assert todo1 == todo2, "Todos with same id should be equal even with different done status"


def test_todo_inequality_different_id() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a")

    assert todo != "a", "Todo should not be equal to string"
    assert todo != 1, "Todo should not be equal to int"
    assert todo != {"id": 1, "text": "a"}, "Todo should not be equal to dict"


def test_todo_hash_consistency_same_id() -> None:
    """Todos with same id should have same hash."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hash_different_ids() -> None:
    """Todos with different ids should likely have different hashes."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")

    # Hash collisions are possible but unlikely for small integers
    # We verify they can coexist in a set
    todo_set = {todo1, todo2}
    assert len(todo_set) == 2, "Todos with different ids should both exist in set"


def test_todo_set_deduplication_by_id() -> None:
    """Todos should be deduplicated by id in a set."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id, different text
    todo3 = Todo(id=2, text="c")

    todo_set = {todo1, todo2, todo3}
    assert len(todo_set) == 2, "Set should contain only 2 unique ids"


def test_todo_dict_key_usage() -> None:
    """Todos should work as dict keys using id-based equality."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id, different text

    mapping = {todo1: "value1"}
    # Since todo1 == todo2, they should map to the same key
    assert mapping[todo2] == "value1", "Equal todos should access same dict entry"


def test_todo_reflexivity() -> None:
    """A todo should be equal to itself."""
    todo = Todo(id=1, text="a")
    assert todo == todo, "Todo should be equal to itself"


def test_todo_symmetry() -> None:
    """Equality should be symmetric."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    assert (todo1 == todo2) == (todo2 == todo1), "Equality should be symmetric"


def test_todo_transitivity() -> None:
    """Equality should be transitive."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    todo3 = Todo(id=1, text="c")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3, "Equality should be transitive"

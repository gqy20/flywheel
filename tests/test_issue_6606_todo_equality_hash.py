"""Tests for Todo.__eq__ and __hash__ methods (Issue #6606).

These tests verify that:
1. Todos with the same id are equal regardless of other fields
2. Todos with different ids are not equal
3. Todo objects can be used in sets and as dict keys
4. Hash is consistent with equality
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id() -> None:
    """Todos with same id should be equal regardless of other fields."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=1, text="b", done=True)  # Same id, different text and done
    assert t1 == t2


def test_todo_equality_same_id_different_timestamps() -> None:
    """Todos with same id should be equal even with different timestamps."""
    t1 = Todo(id=1, text="a", created_at="2024-01-01", updated_at="2024-01-01")
    t2 = Todo(id=1, text="a", created_at="2024-12-31", updated_at="2024-12-31")
    assert t1 == t2


def test_todo_inequality_different_id() -> None:
    """Todos with different ids should not be equal."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = Todo(id=2, text="a", done=False)  # Same everything except id
    assert t1 != t2


def test_todo_inequality_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a")
    assert todo != 1  # Comparing with int
    assert todo != "1"  # Comparing with string
    assert todo != {"id": 1, "text": "a"}  # Comparing with dict
    assert todo is not None  # Comparing with None


def test_todo_hashable_in_set() -> None:
    """Todo objects should be hashable and usable in sets."""
    t1 = Todo(id=1, text="a")
    t2 = Todo(id=1, text="b")  # Same id, should be deduplicated
    t3 = Todo(id=2, text="a")  # Different id
    todo_set = {t1, t2, t3}
    assert len(todo_set) == 2  # t1 and t2 deduplicated


def test_todo_hashable_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    t1 = Todo(id=1, text="a")
    t2 = Todo(id=1, text="b")  # Same id, should map to same entry
    t3 = Todo(id=2, text="c")  # Different id

    d = {t1: "first", t3: "third"}
    d[t2] = "second"  # Should overwrite first entry (same id)

    assert len(d) == 2
    assert d[t1] == "second"  # t1 and t2 are same key


def test_todo_hash_consistent_with_equality() -> None:
    """Equal todos should have same hash."""
    t1 = Todo(id=1, text="a")
    t2 = Todo(id=1, text="b")
    assert hash(t1) == hash(t2)


def test_todo_hash_different_for_different_ids() -> None:
    """Different todos should (likely) have different hashes."""
    t1 = Todo(id=1, text="a")
    t2 = Todo(id=2, text="a")
    # Note: hash collision is theoretically possible but unlikely for ints
    assert hash(t1) != hash(t2)


def test_todo_reflexivity() -> None:
    """A todo should be equal to itself."""
    t = Todo(id=1, text="a")
    assert t == t


def test_todo_symmetry() -> None:
    """Equality should be symmetric: if a == b then b == a."""
    t1 = Todo(id=1, text="a")
    t2 = Todo(id=1, text="b")
    assert t1 == t2
    assert t2 == t1


def test_todo_transitivity() -> None:
    """Equality should be transitive: if a == b and b == c then a == c."""
    t1 = Todo(id=1, text="a")
    t2 = Todo(id=1, text="b")
    t3 = Todo(id=1, text="c")
    assert t1 == t2
    assert t2 == t3
    assert t1 == t3

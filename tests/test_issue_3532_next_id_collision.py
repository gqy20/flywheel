"""Regression tests for issue #3532: next_id() ID collision bug.

Bug: next_id() returns already existing IDs when JSON file has
non-contiguous or deleted IDs (ID gaps/holes).

Root cause: next_id() only considers max(id) + 1, assuming IDs are
contiguous, but remove() can delete any ID creating gaps.

The current implementation already returns max(id) + 1 which is
always unique. This test suite verifies the expected behavior.

Acceptance criteria from issue:
- [1, 3] -> should return 4 (max+1)
- [1, 2, 3], remove 2 -> [1, 3], next_id should return 4
- Empty list -> should return 1
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_gap_returns_non_colliding_id() -> None:
    """Test that next_id() returns a non-colliding ID when gaps exist.

    Acceptance criteria: [1, 3] should return 4 (not 2 to fill gap).
    """
    storage = TodoStorage(":memory:")  # Path doesn't matter for next_id

    # IDs [1, 3] -> next_id should return 4 (max + 1)
    todos = [Todo(id=1, text="a"), Todo(id=3, text="b")]
    assert storage.next_id(todos) == 4


def test_next_id_after_remove_returns_next_available() -> None:
    """Test scenario 2 from issue: remove middle ID, add new.

    Create todos [1, 2, 3], delete id=2, add new todo.
    New ID should be 4 (not 3 to fill gap).
    """
    storage = TodoStorage(":memory:")

    # After removing id=2, we have [1, 3]
    todos = [Todo(id=1, text="a"), Todo(id=3, text="c")]
    # next_id should return 4 (max + 1 = 3 + 1)
    assert storage.next_id(todos) == 4


def test_next_id_empty_list_returns_1() -> None:
    """Test scenario 3: empty list should return 1."""
    storage = TodoStorage(":memory:")
    assert storage.next_id([]) == 1


def test_next_id_with_large_gap() -> None:
    """Test with a large gap between IDs."""
    storage = TodoStorage(":memory:")

    # [1, 100]
    todos = [Todo(id=1, text="a"), Todo(id=100, text="b")]
    # max = 100, max + 1 = 101
    assert storage.next_id(todos) == 101


def test_next_id_with_multiple_gaps() -> None:
    """Test scenario from issue: [1, 3, 5] should return 6."""
    storage = TodoStorage(":memory:")

    todos = [Todo(id=1, text="a"), Todo(id=3, text="b"), Todo(id=5, text="c")]
    assert storage.next_id(todos) == 6


def test_next_id_single_element() -> None:
    """Test with single element."""
    storage = TodoStorage(":memory:")
    todos = [Todo(id=5, text="a")]
    assert storage.next_id(todos) == 6


def test_next_id_consecutive_ids() -> None:
    """Test with consecutive IDs."""
    storage = TodoStorage(":memory:")

    # [1, 2, 3]
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]
    assert storage.next_id(todos) == 4


def test_next_id_add_after_delete_flow(tmp_path) -> None:
    """Integration test: add, delete, add again should not produce duplicate ID."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Add three todos
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    storage.save(todos)

    # Remove the middle one (id=2)
    remaining = [t for t in storage.load() if t.id != 2]
    storage.save(remaining)

    # Add a new todo - should get id=4, not id=2
    loaded = storage.load()
    new_id = storage.next_id(loaded)
    assert new_id == 4, f"Expected 4, got {new_id}"

    # Add the new todo and save
    remaining.append(Todo(id=new_id, text="fourth"))
    storage.save(remaining)

    # Verify no duplicate IDs
    final = storage.load()
    ids = [t.id for t in final]
    assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"
    assert sorted(ids) == [1, 3, 4]

"""Regression test for issue #5029: next_id returns duplicate IDs when todo list has non-contiguous IDs.

The bug occurs because next_id() uses max(id) + 1 instead of finding the first
available gap. This causes duplicate IDs when todos are removed and new ones added.

Example:
- Create todos [1, 2, 3], remove #2 -> [1, 3]
- Add new todo -> current code returns 4, but should return 2 (first available gap)
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_fills_gap_from_removed_todo() -> None:
    """After removing todo #2 from [1,2,3], next_id should return 2, not 4."""
    storage = TodoStorage()

    # Create todos [1, 2, 3]
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]

    # next_id should return 4 for contiguous IDs
    assert storage.next_id(todos) == 4

    # Remove todo #2 -> [1, 3]
    todos = [t for t in todos if t.id != 2]

    # next_id should now return 2 (the first available gap)
    assert storage.next_id(todos) == 2


def test_next_id_finds_first_gap_in_non_contiguous_ids() -> None:
    """For todos with IDs [1, 3, 5], next_id should return 2."""
    storage = TodoStorage()

    todos = [Todo(id=1, text="a"), Todo(id=3, text="b"), Todo(id=5, text="c")]

    # next_id should return 2 (first gap), not 6
    assert storage.next_id(todos) == 2


def test_next_id_returns_1_for_empty_list() -> None:
    """For empty todo list, next_id should return 1."""
    storage = TodoStorage()

    assert storage.next_id([]) == 1


def test_next_id_returns_max_plus_one_for_contiguous_ids() -> None:
    """For contiguous IDs starting at 1, next_id should return max + 1."""
    storage = TodoStorage()

    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]

    assert storage.next_id(todos) == 4


def test_next_id_handles_single_gap_at_start() -> None:
    """If ID 1 is missing, next_id should return 1."""
    storage = TodoStorage()

    todos = [Todo(id=2, text="a"), Todo(id=3, text="b")]

    assert storage.next_id(todos) == 1


def test_next_id_no_duplicate_after_add_remove_cycle(tmp_path) -> None:
    """Integration test: verify no duplicate IDs after add/remove cycles."""
    from flywheel.cli import TodoApp

    app = TodoApp(str(tmp_path / "db.json"))

    # Add 3 todos
    app.add("first")
    app.add("second")
    app.add("third")

    # Remove #2
    app.remove(2)

    # Add new todo - should get ID 2
    new_todo = app.add("fourth")
    assert new_todo.id == 2, f"Expected ID 2 for new todo after removing #2, got {new_todo.id}"

    # Verify no duplicate IDs in storage
    all_todos = app.list()
    ids = [t.id for t in all_todos]
    assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"


def test_next_id_multiple_gaps() -> None:
    """For IDs [1, 4, 7], next_id should return 2 (first gap)."""
    storage = TodoStorage()

    todos = [Todo(id=1, text="a"), Todo(id=4, text="b"), Todo(id=7, text="c")]

    assert storage.next_id(todos) == 2


def test_next_id_preserves_stability_across_save_load(tmp_path) -> None:
    """IDs remain stable and no duplicates across save/load cycles."""
    storage = TodoStorage(str(tmp_path / "db.json"))

    # Save initial todos with gaps
    todos = [Todo(id=1, text="a"), Todo(id=3, text="c")]
    storage.save(todos)

    # Load and get next_id
    loaded = storage.load()
    next_id = storage.next_id(loaded)

    # Add new todo with that ID
    todos.append(Todo(id=next_id, text="new"))
    storage.save(todos)

    # Load again and verify no duplicates
    final = storage.load()
    ids = [t.id for t in final]
    assert len(ids) == len(set(ids)), f"Duplicate IDs after save/load: {ids}"
    assert 2 in ids, "Expected ID 2 to be filled in"

"""Regression tests for issue #5029: next_id returns duplicate IDs with non-contiguous IDs."""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_finds_first_gap_after_removal(tmp_path) -> None:
    """After removing todo #2 from [1,2,3], next_id should return 2 (first available), not 4."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with IDs [1, 2, 3]
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=3, text="third")]
    storage.save(todos)

    # Remove todo #2, leaving [1, 3]
    loaded = storage.load()
    remaining = [t for t in loaded if t.id != 2]

    # next_id should return 2 (the first available gap), not 4
    assert storage.next_id(remaining) == 2


def test_next_id_finds_first_gap_in_non_contiguous_list(tmp_path) -> None:
    """For list with IDs [1, 3, 5], next_id should return 2 (first available)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with non-contiguous IDs [1, 3, 5]
    todos = [Todo(id=1, text="a"), Todo(id=3, text="b"), Todo(id=5, text="c")]
    storage.save(todos)

    loaded = storage.load()

    # next_id should return 2 (the first available gap), not 6
    assert storage.next_id(loaded) == 2


def test_next_id_returns_1_for_empty_list(tmp_path) -> None:
    """For empty todo list, next_id should return 1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Empty list should return 1
    assert storage.next_id([]) == 1


def test_next_id_returns_next_for_contiguous_ids(tmp_path) -> None:
    """For contiguous IDs [1, 2, 3], next_id should return 4."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]
    storage.save(todos)

    loaded = storage.load()
    assert storage.next_id(loaded) == 4


def test_next_id_finds_gap_at_start(tmp_path) -> None:
    """For list starting at ID 2, next_id should return 1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos starting at ID 2
    todos = [Todo(id=2, text="a"), Todo(id=3, text="b")]
    storage.save(todos)

    loaded = storage.load()
    assert storage.next_id(loaded) == 1


def test_no_duplicate_ids_in_full_workflow(tmp_path) -> None:
    """Verify no two todos ever have the same ID in a full workflow."""
    from flywheel.cli import TodoApp

    app = TodoApp(str(tmp_path / "db.json"))

    # Add 3 todos
    app.add("first")
    app.add("second")
    app.add("third")

    # Remove the middle one (ID 2)
    app.remove(2)

    # Add a new todo - should get ID 2, not 4
    new_todo = app.add("new")
    assert new_todo.id == 2, f"Expected ID 2 but got {new_todo.id}"

    # Verify no duplicate IDs in the list
    all_todos = app.list()
    ids = [t.id for t in all_todos]
    assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"

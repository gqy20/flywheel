"""Tests for issue #5748: ID collision when multiple TodoApp instances add todos concurrently."""

from __future__ import annotations

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_next_id_with_collision_detection(tmp_path) -> None:
    """Regression test for #5748: next_id should handle existing IDs in storage.

    This tests the scenario where:
    1. App A loads todos and calculates next_id = 2
    2. App B loads todos and also calculates next_id = 2
    3. App A saves a new todo with id=2
    4. App B tries to save with id=2 - should detect collision and use id=3
    """
    db_path = str(tmp_path / "shared.json")
    storage = TodoStorage(db_path)

    # Start with one todo
    initial = Todo(id=1, text="Initial todo")
    storage.save([initial])

    # Simulate App A: load, get next_id, save
    todos_a = storage.load()
    next_id_a = storage.next_id(todos_a)
    assert next_id_a == 2
    todos_a.append(Todo(id=next_id_a, text="From App A"))
    storage.save(todos_a)

    # Simulate App B: had loaded same initial state, now tries to save
    # It also calculated next_id = 2, but that ID is now taken
    todos_b = [initial]  # App B's stale view
    _ = storage.next_id(todos_b)  # Would be 2, but collision!

    # The fix: storage.next_id_for_save should check current storage
    # and return an ID that doesn't collide
    fresh_id = storage.next_id_for_save()
    assert fresh_id == 3, f"Expected collision-safe id=3, got {fresh_id}"


def test_next_id_for_save_returns_1_for_empty_storage(tmp_path) -> None:
    """next_id_for_save should return 1 for empty storage."""
    db_path = str(tmp_path / "empty.json")
    storage = TodoStorage(db_path)

    assert storage.next_id_for_save() == 1


def test_next_id_for_save_returns_max_plus_one(tmp_path) -> None:
    """next_id_for_save should return max(existing_ids) + 1."""
    db_path = str(tmp_path / "todos.json")
    storage = TodoStorage(db_path)

    storage.save([Todo(id=1, text="A"), Todo(id=3, text="B"), Todo(id=5, text="C")])

    assert storage.next_id_for_save() == 6


def test_concurrent_add_produces_unique_ids(tmp_path) -> None:
    """Regression test for #5748: Multiple TodoApp instances should not produce ID collisions.

    Simulates the race condition where:
    1. Two TodoApp instances share the same storage file
    2. Both load the same state (empty or with existing todos)
    3. Both calculate next_id based on that state
    4. Both save - should not result in duplicate IDs
    """
    db_path = str(tmp_path / "shared.json")

    # Create two app instances pointing to same storage
    app1 = TodoApp(db_path)
    app2 = TodoApp(db_path)

    # Both start with empty state
    assert app1.list() == []
    assert app2.list() == []

    # App1 adds first todo
    todo1 = app1.add("First from app1")
    assert todo1.id == 1

    # App2 adds - should get unique ID (using next_id_for_save internally)
    todo2 = app2.add("First from app2")

    # Both todos should have unique IDs
    assert todo1.id != todo2.id, f"ID collision detected: both got id={todo1.id}"

    # Verify the storage has both todos with unique IDs
    storage = TodoStorage(db_path)
    loaded = storage.load()
    ids = [t.id for t in loaded]
    assert len(ids) == len(set(ids)), f"Duplicate IDs in storage: {ids}"


def test_concurrent_add_with_existing_todos(tmp_path) -> None:
    """Regression test for #5748: Collision with pre-existing todos."""

    db_path = str(tmp_path / "shared.json")

    # Pre-populate with some todos
    app = TodoApp(db_path)
    app.add("Existing 1")  # id=1
    app.add("Existing 2")  # id=2
    app.add("Existing 3")  # id=3

    # Create two new app instances (both see same state)
    app1 = TodoApp(db_path)
    app2 = TodoApp(db_path)

    # Both calculate next_id = 4 based on current state
    # App1 adds successfully
    todo1 = app1.add("New from app1")
    assert todo1.id == 4

    # App2 should detect collision and use id=5 instead
    todo2 = app2.add("New from app2")
    assert todo2.id == 5, f"Expected id=5 but got id={todo2.id} (collision not handled)"

    # Verify storage integrity
    storage = TodoStorage(db_path)
    loaded = storage.load()
    ids = [t.id for t in loaded]
    assert sorted(ids) == [1, 2, 3, 4, 5]

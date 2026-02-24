"""Tests for issue #5611: next_id() should return unique IDs with non-contiguous IDs.

This test suite verifies that next_id() returns unique IDs even when todos have
non-contiguous IDs with gaps (e.g., [1, 3, 5] should return 2, not 6).
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_single_gap(tmp_path: Path) -> None:
    """Test that next_id returns the first available ID when there's a gap at position 1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with IDs [2, 3] - gap at 1
    todos = [Todo(id=2, text="second"), Todo(id=3, text="third")]
    storage.save(todos)

    # next_id should return 1 (filling the gap), not 4
    new_id = storage.next_id(storage.load())
    assert new_id == 1, f"Expected 1 (first gap), got {new_id}"


def test_next_id_with_multiple_gaps(tmp_path: Path) -> None:
    """Test that next_id returns the first available ID when there are multiple gaps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with IDs [1, 3, 5] - gaps at 2 and 4
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
        Todo(id=5, text="fifth"),
    ]
    storage.save(todos)

    # next_id should return 2 (first gap), not 6
    new_id = storage.next_id(storage.load())
    assert new_id == 2, f"Expected 2 (first gap), got {new_id}"


def test_next_id_with_gap_at_end(tmp_path: Path) -> None:
    """Test that next_id returns first gap, not max+1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with IDs [1, 2, 10] - gaps at 3-9
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=10, text="tenth"),
    ]
    storage.save(todos)

    # next_id should return 3 (first gap), not 11
    new_id = storage.next_id(storage.load())
    assert new_id == 3, f"Expected 3 (first gap), got {new_id}"


def test_next_id_returns_unique_ids_sequentially(tmp_path: Path) -> None:
    """Test that calling next_id multiple times returns unique IDs filling gaps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Start with IDs [2, 4]
    todos = [Todo(id=2, text="second"), Todo(id=4, text="fourth")]
    storage.save(todos)

    # First call should return 1
    loaded = storage.load()
    new_id1 = storage.next_id(loaded)
    assert new_id1 == 1

    # Add the todo with ID 1
    loaded.append(Todo(id=new_id1, text="first"))
    storage.save(loaded)

    # Second call should return 3
    loaded = storage.load()
    new_id2 = storage.next_id(loaded)
    assert new_id2 == 3

    # Add the todo with ID 3
    loaded.append(Todo(id=new_id2, text="third"))
    storage.save(loaded)

    # Third call should return 5 (no more gaps)
    loaded = storage.load()
    new_id3 = storage.next_id(loaded)
    assert new_id3 == 5


def test_next_id_empty_list_returns_one(tmp_path: Path) -> None:
    """Test that next_id returns 1 for empty list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Empty list
    new_id = storage.next_id([])
    assert new_id == 1


def test_next_id_contiguous_ids_returns_next(tmp_path: Path) -> None:
    """Test that next_id returns max+1 when IDs are contiguous."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Contiguous IDs [1, 2, 3]
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    storage.save(todos)

    # next_id should return 4
    new_id = storage.next_id(storage.load())
    assert new_id == 4


def test_next_id_preserves_uniqueness_with_gaps(tmp_path: Path) -> None:
    """Test that sequential add operations produce unique IDs even with gaps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Start with sparse IDs
    todos = [Todo(id=10, text="tenth")]
    storage.save(todos)

    # Add multiple todos sequentially - each should get a unique ID
    used_ids = {10}
    for i in range(5):
        loaded = storage.load()
        new_id = storage.next_id(loaded)
        assert new_id not in used_ids, f"Duplicate ID {new_id} generated on iteration {i}"
        used_ids.add(new_id)
        loaded.append(Todo(id=new_id, text=f"todo-{i}"))
        storage.save(loaded)

    # Verify all IDs are unique
    final_todos = storage.load()
    all_ids = [t.id for t in final_todos]
    assert len(all_ids) == len(set(all_ids)), "All IDs should be unique"

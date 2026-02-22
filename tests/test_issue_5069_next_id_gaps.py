"""Tests for issue #5069: next_id should handle non-contiguous IDs correctly."""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_finds_first_gap_when_todos_have_non_contiguous_ids(tmp_path) -> None:
    """Bug #5069: next_id should return the smallest unused positive integer.

    When todos have non-contiguous IDs like [1, 3, 5], next_id should
    return 2 (the smallest unused ID), not 6 (max + 1).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with non-contiguous IDs: 1, 3, 5
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
        Todo(id=5, text="fifth"),
    ]

    # next_id should return 2 (first gap), not 6
    assert storage.next_id(todos) == 2


def test_next_id_returns_1_for_empty_list(tmp_path) -> None:
    """next_id should return 1 when no todos exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    assert storage.next_id([]) == 1


def test_next_id_finds_first_gap_at_start(tmp_path) -> None:
    """When ID 1 is missing, next_id should return 1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=2, text="second"), Todo(id=3, text="third")]

    assert storage.next_id(todos) == 1


def test_next_id_finds_gap_in_middle(tmp_path) -> None:
    """When there's a gap in the middle, next_id should find it."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="first"), Todo(id=4, text="fourth")]

    # Gap at 2 and 3 - should return 2 (smallest)
    assert storage.next_id(todos) == 2


def test_next_id_returns_max_plus_1_when_no_gaps(tmp_path) -> None:
    """When there are no gaps, next_id should return max + 1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]

    assert storage.next_id(todos) == 3


def test_next_id_handles_single_todo(tmp_path) -> None:
    """next_id should work with a single todo."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=5, text="fifth")]
    assert storage.next_id(todos) == 1


def test_next_id_prevents_duplicate_ids_after_deletion(tmp_path) -> None:
    """Bug #5069: Ensure no duplicate IDs when max-ID todo is deleted.

    This simulates the real-world scenario:
    1. Add todos [1, 2, 3]
    2. Delete todo 3
    3. Add new todo - should get ID 3 (the gap), not duplicate an existing ID
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate: had [1, 2, 3], then deleted 3
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]

    # next_id should return 3 (filling the gap), ensuring no duplicates
    assert storage.next_id(todos) == 3

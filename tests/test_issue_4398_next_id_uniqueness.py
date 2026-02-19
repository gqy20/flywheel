"""Tests for issue #4398: next_id should ensure ID uniqueness.

Bug description:
- next_id returns max+1, which can cause ID conflicts when there are non-contiguous IDs
- With IDs like [1, 3, 5], next_id returns 6 instead of 2
- This can cause ID conflicts if someone manually adds a todo with a lower ID later

Acceptance criteria:
- When JSON file contains non-contiguous IDs (e.g., [1, 3, 5]), new Todo ID should not conflict
- next_id should return the smallest unused positive integer
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_smallest_unused_with_non_contiguous_ids(tmp_path: Path) -> None:
    """Bug #4398: next_id should return smallest unused ID, not max+1.

    When JSON file has non-contiguous IDs like [1, 3, 5], next_id should
    return 2 (the smallest unused positive integer), not 6 (max+1).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with non-contiguous IDs
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
        Todo(id=5, text="fifth"),
    ]
    storage.save(todos)

    # next_id should return 2, the smallest unused positive integer
    loaded = storage.load()
    assert storage.next_id(loaded) == 2


def test_next_id_returns_one_when_empty(tmp_path: Path) -> None:
    """When no todos exist, next_id should return 1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = storage.load()
    assert len(todos) == 0
    assert storage.next_id(todos) == 1


def test_next_id_returns_next_when_contiguous(tmp_path: Path) -> None:
    """When todos are contiguous starting from 1, next_id should return max+1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    storage.save(todos)

    loaded = storage.load()
    assert storage.next_id(loaded) == 4


def test_next_id_handles_gap_at_start(tmp_path: Path) -> None:
    """When first ID is not 1, next_id should return 1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Start from ID 3
    todos = [
        Todo(id=3, text="third"),
        Todo(id=5, text="fifth"),
    ]
    storage.save(todos)

    loaded = storage.load()
    assert storage.next_id(loaded) == 1


def test_next_id_with_multiple_gaps(tmp_path: Path) -> None:
    """next_id should find the smallest gap even with multiple gaps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # IDs: 2, 3, 6, 10 - smallest unused is 1
    todos = [
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
        Todo(id=6, text="sixth"),
        Todo(id=10, text="tenth"),
    ]
    storage.save(todos)

    loaded = storage.load()
    assert storage.next_id(loaded) == 1

    # Now add id=1, smallest unused should be 4
    todos.append(Todo(id=1, text="first"))
    storage.save(todos)

    loaded = storage.load()
    assert storage.next_id(loaded) == 4

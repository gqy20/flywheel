"""Tests for load_stats() method returning storage metadata.

This test suite verifies that TodoStorage.load_stats() returns
a dictionary with total, done, and pending counts.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_stats_empty_database(tmp_path: Path) -> None:
    """Test load_stats returns all zeros for empty/non-existent database."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Database doesn't exist yet
    stats = storage.load_stats()

    assert stats["total"] == 0
    assert stats["done"] == 0
    assert stats["pending"] == 0


def test_load_stats_with_todos(tmp_path: Path) -> None:
    """Test load_stats returns correct counts for todos."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos: 2 done, 3 pending
    todos = [
        Todo(id=1, text="done task 1", done=True),
        Todo(id=2, text="done task 2", done=True),
        Todo(id=3, text="pending task 1", done=False),
        Todo(id=4, text="pending task 2", done=False),
        Todo(id=5, text="pending task 3", done=False),
    ]
    storage.save(todos)

    stats = storage.load_stats()

    assert stats["total"] == 5
    assert stats["done"] == 2
    assert stats["pending"] == 3


def test_load_stats_all_done(tmp_path: Path) -> None:
    """Test load_stats when all todos are done."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="task 1", done=True),
        Todo(id=2, text="task 2", done=True),
    ]
    storage.save(todos)

    stats = storage.load_stats()

    assert stats["total"] == 2
    assert stats["done"] == 2
    assert stats["pending"] == 0


def test_load_stats_all_pending(tmp_path: Path) -> None:
    """Test load_stats when all todos are pending."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="task 1", done=False),
        Todo(id=2, text="task 2", done=False),
    ]
    storage.save(todos)

    stats = storage.load_stats()

    assert stats["total"] == 2
    assert stats["done"] == 0
    assert stats["pending"] == 2

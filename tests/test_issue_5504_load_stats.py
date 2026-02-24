"""Tests for issue #5504: load_stats() method.

This test suite verifies that TodoStorage.load_stats() returns
a dictionary with total, done, and pending counts.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_stats_empty_database(tmp_path: Path) -> None:
    """Test that load_stats() returns all zeros for empty database."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    stats = storage.load_stats()

    assert stats == {"total": 0, "done": 0, "pending": 0}


def test_load_stats_with_todos(tmp_path: Path) -> None:
    """Test that load_stats() returns correct counts for mixed todos."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Create 5 todos: 2 done, 3 pending
    todos = [
        Todo(id=1, text="task 1", done=True),
        Todo(id=2, text="task 2", done=True),
        Todo(id=3, text="task 3", done=False),
        Todo(id=4, text="task 4", done=False),
        Todo(id=5, text="task 5", done=False),
    ]
    storage.save(todos)

    stats = storage.load_stats()

    assert stats == {"total": 5, "done": 2, "pending": 3}


def test_load_stats_all_done(tmp_path: Path) -> None:
    """Test that load_stats() returns correct counts when all todos are done."""
    db = tmp_path / "all_done.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="completed 1", done=True),
        Todo(id=2, text="completed 2", done=True),
    ]
    storage.save(todos)

    stats = storage.load_stats()

    assert stats == {"total": 2, "done": 2, "pending": 0}


def test_load_stats_all_pending(tmp_path: Path) -> None:
    """Test that load_stats() returns correct counts when all todos are pending."""
    db = tmp_path / "all_pending.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="pending 1", done=False),
        Todo(id=2, text="pending 2", done=False),
        Todo(id=3, text="pending 3", done=False),
    ]
    storage.save(todos)

    stats = storage.load_stats()

    assert stats == {"total": 3, "done": 0, "pending": 3}


def test_load_stats_returns_dict(tmp_path: Path) -> None:
    """Test that load_stats() returns a dictionary with correct keys."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    stats = storage.load_stats()

    assert isinstance(stats, dict)
    assert "total" in stats
    assert "done" in stats
    assert "pending" in stats

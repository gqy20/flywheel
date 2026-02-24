"""Tests for load_stats() method in TodoStorage.

Issue #5504: Add load_stats() method to return storage metadata.
This provides a convenient way to get todo statistics (total, done, pending)
without having to load and count todos manually.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_stats_returns_zero_for_empty_database(tmp_path: Path) -> None:
    """Test that load_stats() returns all zeros for empty/non-existent database."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    stats = storage.load_stats()

    assert stats == {"total": 0, "done": 0, "pending": 0}


def test_load_stats_counts_todos_correctly(tmp_path: Path) -> None:
    """Test that load_stats() correctly counts total, done, and pending todos."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a mix of done and pending todos
    todos = [
        Todo(id=1, text="pending task 1", done=False),
        Todo(id=2, text="done task 1", done=True),
        Todo(id=3, text="pending task 2", done=False),
        Todo(id=4, text="done task 2", done=True),
        Todo(id=5, text="done task 3", done=True),
    ]
    storage.save(todos)

    stats = storage.load_stats()

    assert stats == {"total": 5, "done": 3, "pending": 2}


def test_load_stats_with_only_pending_todos(tmp_path: Path) -> None:
    """Test load_stats() with only pending (not done) todos."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="task 1", done=False),
        Todo(id=2, text="task 2", done=False),
    ]
    storage.save(todos)

    stats = storage.load_stats()

    assert stats == {"total": 2, "done": 0, "pending": 2}


def test_load_stats_with_only_done_todos(tmp_path: Path) -> None:
    """Test load_stats() with only done todos."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="task 1", done=True),
        Todo(id=2, text="task 2", done=True),
        Todo(id=3, text="task 3", done=True),
    ]
    storage.save(todos)

    stats = storage.load_stats()

    assert stats == {"total": 3, "done": 3, "pending": 0}


def test_load_stats_returns_dict_with_expected_keys(tmp_path: Path) -> None:
    """Test that load_stats() returns a dict with exactly the expected keys."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    stats = storage.load_stats()

    assert isinstance(stats, dict)
    assert set(stats.keys()) == {"total", "done", "pending"}
    assert all(isinstance(v, int) for v in stats.values())

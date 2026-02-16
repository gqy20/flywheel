"""Tests for TodoStorage.next_id().

This test suite verifies that next_id() correctly generates unique IDs
even when the todo list contains duplicate IDs.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_1_for_empty_list(tmp_path: Path) -> None:
    """Test that next_id returns 1 for an empty todo list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    result = storage.next_id([])

    assert result == 1


def test_next_id_returns_max_plus_one(tmp_path: Path) -> None:
    """Test that next_id returns max(id) + 1 for a normal todo list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="first"), Todo(id=3, text="second"), Todo(id=5, text="third")]

    result = storage.next_id(todos)

    assert result == 6


def test_next_id_handles_duplicate_ids(tmp_path: Path) -> None:
    """Regression test for issue #3593: next_id must return unique ID even with duplicates.

    If the todo list contains duplicate IDs, next_id() should still return
    a valid unused ID (max + 1), not a duplicate of an existing ID.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with duplicate IDs (this can happen due to data corruption or bugs)
    todos = [Todo(id=1, text="first"), Todo(id=1, text="duplicate of first")]

    result = storage.next_id(todos)

    # Should return 2 (max + 1), not 2 that could conflict with existing
    # But more importantly, should not return 1 which is already used
    assert result == 2
    assert result not in {todo.id for todo in todos}


def test_next_id_handles_multiple_duplicate_ids(tmp_path: Path) -> None:
    """Test next_id with multiple sets of duplicate IDs."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="a"),
        Todo(id=1, text="b"),
        Todo(id=3, text="c"),
        Todo(id=3, text="d"),
        Todo(id=5, text="e"),
    ]

    result = storage.next_id(todos)

    # Max ID is 5, so next should be 6
    assert result == 6
    # Verify it's unique
    assert result not in {todo.id for todo in todos}

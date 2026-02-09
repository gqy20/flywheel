"""Regression test for issue #2428: next_id() consistency.

Tests that next_id() returns consistent values for both empty and non-empty lists.
The function should simplify to: max((todo.id for todo in todos), default=0) + 1
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_one_for_empty_list() -> None:
    """Issue #2428: next_id([]) should return 1."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_returns_max_plus_one_for_non_empty_list() -> None:
    """Issue #2428: next_id([Todo(id=1), Todo(id=2)]) should return 3."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b")]
    assert storage.next_id(todos) == 3


def test_next_id_handles_gaps_in_ids() -> None:
    """Issue #2428: next_id() should return max(id) + 1 even with gaps."""
    storage = TodoStorage()
    # If ids are 1, 5, 10, next_id should return 11 (max + 1)
    todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=10, text="c")]
    assert storage.next_id(todos) == 11


def test_app_add_creates_id_one_in_empty_database(tmp_path) -> None:
    """Issue #2428: TodoApp.add() should create id=1 in empty database."""
    from flywheel.cli import TodoApp

    app = TodoApp(str(tmp_path / "db.json"))
    todo = app.add("first todo")
    assert todo.id == 1

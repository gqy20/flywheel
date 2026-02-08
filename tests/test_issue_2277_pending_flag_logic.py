"""Tests for --pending flag logic fix (Issue #2277).

These tests verify that:
1. `todo list` without flags shows only pending todos by default
2. `todo list --all` shows all todos including completed ones
3. The --pending flag is replaced with --all for better UX
"""

from __future__ import annotations

import tempfile

from flywheel.cli import TodoApp


def test_list_default_shows_only_pending(tmp_path: tempfile.PathLike) -> None:
    """`todo list` without flags should show only pending todos by default.

    This is the main issue #2277 - previously the default showed all todos.
    """
    db_path = tmp_path / "test1.json"
    app = TodoApp(db_path=str(db_path))

    # Add some todos
    app.add("task 1")
    app.add("task 2")
    app.add("task 3")

    # Mark one as done
    app.mark_done(2)

    # Default list should show only pending todos (1 and 3, not 2)
    todos = app.list()
    assert len(todos) == 2
    todo_ids = [todo.id for todo in todos]
    assert 1 in todo_ids
    assert 2 not in todo_ids  # Done task should NOT appear
    assert 3 in todo_ids


def test_list_with_show_all_true_shows_all(tmp_path: tempfile.PathLike) -> None:
    """`todo list` with show_all=True should show all todos including completed ones."""
    db_path = tmp_path / "test2.json"
    app = TodoApp(db_path=str(db_path))

    # Add some todos
    app.add("task 1")
    app.add("task 2")
    app.add("task 3")

    # Mark one as done
    app.mark_done(2)

    # With show_all=True, all todos should appear
    todos = app.list(show_all=True)
    assert len(todos) == 3
    todo_ids = [todo.id for todo in todos]
    assert 1 in todo_ids
    assert 2 in todo_ids  # Done task SHOULD appear with show_all=True
    assert 3 in todo_ids


def test_list_with_show_all_false_shows_only_pending(tmp_path: tempfile.PathLike) -> None:
    """`todo list` with show_all=False should show only pending todos."""
    db_path = tmp_path / "test3.json"
    app = TodoApp(db_path=str(db_path))

    # Add some todos
    app.add("task 1")
    app.add("task 2")
    app.add("task 3")

    # Mark one as done
    app.mark_done(2)

    # With show_all=False, only pending todos should appear
    todos = app.list(show_all=False)
    assert len(todos) == 2
    todo_ids = [todo.id for todo in todos]
    assert 1 in todo_ids
    assert 2 not in todo_ids  # Done task should NOT appear
    assert 3 in todo_ids


def test_list_default_with_all_done(tmp_path: tempfile.PathLike) -> None:
    """When all todos are done, default list should return empty list."""
    db_path = tmp_path / "test4.json"
    app = TodoApp(db_path=str(db_path))

    # Add todos
    app.add("task 1")
    app.add("task 2")

    # Mark all as done
    app.mark_done(1)
    app.mark_done(2)

    # Default list should return empty (no pending todos)
    todos = app.list()
    assert len(todos) == 0

    # But with show_all=True, should return both
    all_todos = app.list(show_all=True)
    assert len(all_todos) == 2

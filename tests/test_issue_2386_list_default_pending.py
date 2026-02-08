"""Regression tests for Issue #2386: TodoApp.list() default parameter show_all=True is inconsistent with CLI.

This test file ensures that TodoApp.list() defaults to showing only pending todos,
making the API consistent with CLI behavior expectations.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_todo_app_list_default_shows_only_pending(tmp_path) -> None:
    """TodoApp.list() with no parameters should show only pending todos.

    This is the fix for issue #2386 - the default should be show_all=False
    so that the API shows pending todos by default, which is more intuitive
    for a todo application.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add two todos
    app.add("pending task")
    todo2 = app.add("task to mark done")

    # Mark one as done
    app.mark_done(todo2.id)

    # Call list() without parameters - should show only pending todos
    todos = app.list()
    assert len(todos) == 1, f"Expected 1 pending todo, got {len(todos)}"
    assert todos[0].id == 1, "Should return the pending todo (id=1)"
    assert todos[0].done is False, "Returned todo should be pending"


def test_todo_app_list_pending_shows_only_pending(tmp_path) -> None:
    """TodoApp.list(show_all=False) should show only pending todos."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    app.add("pending task 1")
    todo2 = app.add("task to mark done")
    app.add("pending task 3")

    # Mark one as done
    app.mark_done(todo2.id)

    # Call list(show_all=False) - should show only pending todos
    todos = app.list(show_all=False)
    assert len(todos) == 2, f"Expected 2 pending todos, got {len(todos)}"
    assert all(not todo.done for todo in todos), "All returned todos should be pending"


def test_todo_app_list_all_shows_all_todos(tmp_path) -> None:
    """TodoApp.list(show_all=True) should show all todos (pending and done)."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    app.add("pending task 1")
    todo2 = app.add("task to mark done")
    app.add("pending task 3")

    # Mark one as done
    app.mark_done(todo2.id)

    # Call list(show_all=True) - should show all todos
    todos = app.list(show_all=True)
    assert len(todos) == 3, f"Expected 3 todos total, got {len(todos)}"
    assert todos[0].done is False
    assert todos[1].done is True
    assert todos[2].done is False


def test_cli_list_default_shows_all_todos(tmp_path, capsys) -> None:
    """CLI 'list' without flags should show all todos (pending and done).

    The CLI uses show_all=not args.pending, so when --pending is not set,
    show_all=True, which shows all todos. This behavior is correct per
    the issue acceptance criteria.
    """
    db = tmp_path / "test.json"

    # Setup: add todos and mark one as done
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "pending task"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "done task"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "done", "2"])
    run_command(args)

    # List without flags - should show all todos
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Should show both pending and done todos
    assert "[ ]" in captured.out, "Should show pending todo"
    assert "[x]" in captured.out, "Should show done todo"


def test_cli_list_pending_shows_only_pending(tmp_path, capsys) -> None:
    """CLI 'list --pending' should show only pending todos.

    The --pending flag sets args.pending=True, which makes show_all=False,
    showing only pending todos.
    """
    db = tmp_path / "test.json"

    # Setup: add todos and mark one as done
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "pending task"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "done task"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "done", "2"])
    run_command(args)

    # List with --pending flag - should show only pending todos
    args = parser.parse_args(["--db", str(db), "list", "--pending"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Should show only pending todo
    assert "[ ]" in captured.out, "Should show pending todo"
    assert "[x]" not in captured.out, "Should NOT show done todo"


def test_cli_list_empty_database(tmp_path, capsys) -> None:
    """CLI 'list' on empty database should show appropriate message."""
    db = tmp_path / "test.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    assert "No todos yet" in captured.out

"""Regression tests for Issue #2386: TodoApp.list() default parameter show_all=True is inconsistent with CLI --pending flag.

This test file ensures that:
1. TodoApp.list() defaults to showing only pending todos (show_all=False)
2. CLI list command without flags shows only pending todos
3. CLI list command with --all flag shows all todos (pending and done)
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_todoapp_list_default_shows_only_pending(tmp_path) -> None:
    """TodoApp.list() with no arguments should show only pending todos.

    This is the fix for issue #2386 - the default should be show_all=False
    so that calling list() without arguments shows only pending (not done) todos.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add three todos
    app.add("task1")
    app.add("task2")
    app.add("task3")

    # Mark one as done
    app.mark_done(2)

    # Default list() should show only pending (task1 and task3, not task2)
    todos = app.list()
    assert len(todos) == 2, f"Expected 2 pending todos, got {len(todos)}"
    assert all(not todo.done for todo in todos), "All returned todos should be pending"
    assert todos[0].id == 1
    assert todos[1].id == 3


def test_todoapp_list_show_all_true_returns_all(tmp_path) -> None:
    """TodoApp.list(show_all=True) should return all todos including done ones."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add three todos
    app.add("task1")
    app.add("task2")
    app.add("task3")

    # Mark one as done
    app.mark_done(2)

    # list(show_all=True) should show all three todos
    todos = app.list(show_all=True)
    assert len(todos) == 3, f"Expected 3 todos, got {len(todos)}"
    assert [todo.id for todo in todos] == [1, 2, 3]


def test_cli_list_default_shows_only_pending(tmp_path, capsys) -> None:
    """CLI 'list' command without flags should show only pending todos.

    This is the user-facing behavior fix - running 'todo list' without
    any flags should only show pending (not done) todos.
    """
    db = tmp_path / "test.json"
    parser = build_parser()

    # Add three todos
    args = parser.parse_args(["--db", str(db), "add", "task1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "task2"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "task3"])
    run_command(args)

    # Mark one as done
    args = parser.parse_args(["--db", str(db), "done", "2"])
    run_command(args)

    # Clear previous output
    capsys.readouterr()

    # List without flags should show only pending todos
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Should show task1 and task3, but NOT task2 (done)
    assert "task1" in captured.out
    assert "task3" in captured.out
    # task2 should not appear in the list output (it's done)
    # Check that there's no line with task2 in the list format
    lines = captured.out.split("\n")
    list_lines = [line for line in lines if line.strip().startswith("[")]
    assert len(list_lines) == 2, f"Expected 2 items in list, got {len(list_lines)}"
    assert any("task1" in line for line in list_lines)
    assert any("task3" in line for line in list_lines)
    assert not any("task2" in line for line in list_lines)


def test_cli_list_with_all_flag_shows_all(tmp_path, capsys) -> None:
    """CLI 'list --all' command should show all todos including done ones.

    The --all flag replaces --pending to show completed items too.
    """
    db = tmp_path / "test.json"
    parser = build_parser()

    # Add three todos
    args = parser.parse_args(["--db", str(db), "add", "task1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "task2"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "task3"])
    run_command(args)

    # Mark one as done
    args = parser.parse_args(["--db", str(db), "done", "2"])
    run_command(args)

    # List with --all should show all three todos
    args = parser.parse_args(["--db", str(db), "list", "--all"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Should show all three tasks
    assert "task1" in captured.out
    assert "task2" in captured.out
    assert "task3" in captured.out

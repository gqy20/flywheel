"""Regression tests for Issue #2386: TodoApp.list() default parameter show_all=True
is inconsistent with CLI --pending flag behavior.

The fix changes the behavior to be more intuitive:
1. TodoApp.list() default parameter changed from show_all=True to show_all=False
2. CLI now has --all flag to explicitly show all todos
3. Default behavior (no flags) shows only pending todos
4. --pending flag shows only pending todos (same as default, but explicit)

Acceptance criteria (updated):
- CLI list command without flags should show only pending todos (not done)
- CLI list command with --all flag should show all todos (both pending and done)
- CLI list command with --pending flag should show only pending todos (explicit)
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_list_default_shows_only_pending_todos(tmp_path, capsys) -> None:
    """CLI list without flags should show ONLY pending todos (not done)."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # Add two todos
    args = parser.parse_args(["--db", str(db), "add", "task1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "task2"])
    run_command(args)

    # Mark one as done
    args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(args)

    # Clear previous output
    capsys.readouterr()

    # List without flags - should show ONLY pending todos (not done)
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Should show only task2 (pending), not task1 (done)
    assert "task2" in captured.out
    assert "task1" not in captured.out


def test_list_with_all_flag_shows_all_todos(tmp_path, capsys) -> None:
    """CLI list with --all flag should show ALL todos (both pending and done)."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # Add two todos
    args = parser.parse_args(["--db", str(db), "add", "task1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "task2"])
    run_command(args)

    # Mark one as done
    args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(args)

    # Clear previous output
    capsys.readouterr()

    # List with --all flag - should show BOTH pending and done
    args = parser.parse_args(["--db", str(db), "list", "--all"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Should show both todos
    assert "task1" in captured.out
    assert "task2" in captured.out


def test_list_pending_shows_only_pending(tmp_path, capsys) -> None:
    """CLI list with --pending flag should show ONLY pending (not done) todos."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # Add two todos
    args = parser.parse_args(["--db", str(db), "add", "task1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "task2"])
    run_command(args)

    # Mark one as done
    args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(args)

    # Clear previous output
    capsys.readouterr()

    # List with --pending flag - should show ONLY pending todos
    args = parser.parse_args(["--db", str(db), "list", "--pending"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Should show only task2 (pending), not task1 (done)
    assert "task2" in captured.out
    assert "task1" not in captured.out


def test_todo_app_list_default_shows_only_pending(tmp_path) -> None:
    """TodoApp.list() with default show_all=False should show only pending todos."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add two todos
    app.add("task1")
    app.add("task2")

    # Mark one as done
    app.mark_done(1)

    # Default list() should show only pending (not done)
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].id == 2  # Only task2 is pending
    assert not todos[0].done


def test_todo_app_list_show_all_false_shows_only_pending(tmp_path) -> None:
    """TodoApp.list(show_all=False) should show only pending todos."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add two todos
    app.add("task1")
    app.add("task2")

    # Mark one as done
    app.mark_done(1)

    # list(show_all=False) should show only pending
    todos = app.list(show_all=False)
    assert len(todos) == 1
    assert todos[0].id == 2  # Only task2 is pending
    assert not todos[0].done


def test_cli_list_all_flag_integration(tmp_path, capsys) -> None:
    """Integration test for CLI --all and --pending flag behavior.

    This test verifies the full workflow:
    1. Add todos
    2. Mark some as done
    3. List without flags shows only pending (new default behavior)
    4. List with --all shows all todos
    5. List with --pending shows only pending (same as default)
    """
    db = tmp_path / "test.json"
    parser = build_parser()

    # Add three todos
    for i in range(1, 4):
        args = parser.parse_args(["--db", str(db), "add", f"task{i}"])
        run_command(args)

    # Mark task1 and task2 as done
    args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "done", "2"])
    run_command(args)

    # Clear previous output
    capsys.readouterr()

    # List without flags - should show only pending (task3 only)
    args = parser.parse_args(["--db", str(db), "list"])
    run_command(args)
    captured_default = capsys.readouterr()
    assert "task3" in captured_default.out
    assert "task1" not in captured_default.out
    assert "task2" not in captured_default.out

    # List with --all - should show all 3 todos
    args = parser.parse_args(["--db", str(db), "list", "--all"])
    run_command(args)
    captured_all = capsys.readouterr()
    assert "task1" in captured_all.out
    assert "task2" in captured_all.out
    assert "task3" in captured_all.out

    # List with --pending - should show only task3 (same as default)
    args = parser.parse_args(["--db", str(db), "list", "--pending"])
    run_command(args)
    captured_pending = capsys.readouterr()
    assert "task3" in captured_pending.out
    assert "task1" not in captured_pending.out
    assert "task2" not in captured_pending.out

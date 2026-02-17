"""Regression tests for Issue #4078: CLI missing 'clear' command.

This test file ensures that the 'clear' command properly batch-deletes
all completed todos and provides appropriate feedback.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_clear_command_deletes_completed_todos(tmp_path, capsys) -> None:
    """'todo clear' should delete all todos where done=True."""
    db = tmp_path / "test.json"

    parser = build_parser()

    # Add 3 todos
    args = parser.parse_args(["--db", str(db), "add", "Task 1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "Task 2"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "Task 3"])
    run_command(args)

    # Mark 2 as done
    args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "done", "2"])
    run_command(args)

    # Run clear command
    args = parser.parse_args(["--db", str(db), "clear"])
    result = run_command(args)

    assert result == 0, "clear command should return 0 on success"

    captured = capsys.readouterr()
    assert "Cleared 2 completed todos" in captured.out

    # Verify only 1 todo remains (the uncompleted one)
    args = parser.parse_args(["--db", str(db), "list"])
    run_command(args)
    captured = capsys.readouterr()
    # Only Task 3 should remain
    assert "Task 1" not in captured.out
    assert "Task 2" not in captured.out
    assert "Task 3" in captured.out


def test_cli_clear_command_no_completed_todos(tmp_path, capsys) -> None:
    """'todo clear' should output 'No completed todos to clear' when none exist."""
    db = tmp_path / "test.json"

    parser = build_parser()

    # Add 2 todos but don't mark any as done
    args = parser.parse_args(["--db", str(db), "add", "Task 1"])
    run_command(args)
    args = parser.parse_args(["--db", str(db), "add", "Task 2"])
    run_command(args)

    # Run clear command
    args = parser.parse_args(["--db", str(db), "clear"])
    result = run_command(args)

    assert result == 0, "clear command should return 0 even when no completed todos"

    captured = capsys.readouterr()
    assert "No completed todos to clear" in captured.out

    # Verify all todos still exist
    args = parser.parse_args(["--db", str(db), "list"])
    run_command(args)
    captured = capsys.readouterr()
    assert "Task 1" in captured.out
    assert "Task 2" in captured.out


def test_cli_clear_command_empty_database(tmp_path, capsys) -> None:
    """'todo clear' should handle empty database gracefully."""
    db = tmp_path / "test.json"

    parser = build_parser()

    # Run clear command on empty database
    args = parser.parse_args(["--db", str(db), "clear"])
    result = run_command(args)

    assert result == 0, "clear command should return 0 on empty database"

    captured = capsys.readouterr()
    assert "No completed todos to clear" in captured.out


def test_todoapp_clear_completed_method(tmp_path) -> None:
    """TodoApp.clear_completed() should return count of deleted todos."""
    from flywheel.cli import TodoApp

    db_path = str(tmp_path / "test.json")
    app = TodoApp(db_path=db_path)

    # Add 3 todos
    app.add("Task 1")
    app.add("Task 2")
    app.add("Task 3")

    # Mark 2 as done
    app.mark_done(1)
    app.mark_done(2)

    # Clear completed
    count = app.clear_completed()

    assert count == 2, "clear_completed should return count of deleted todos"

    # Verify only 1 todo remains
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "Task 3"
    assert todos[0].done is False

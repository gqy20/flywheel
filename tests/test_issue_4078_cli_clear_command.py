"""Regression tests for Issue #4078: CLI missing 'clear' command to batch delete completed todos.

This test file ensures that the 'clear' command works correctly:
- Deletes all done=True tasks
- Outputs 'Cleared N completed todos' when tasks are cleared
- Outputs 'No completed todos to clear' when no completed tasks exist
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_clear_deletes_completed_todos(tmp_path, capsys) -> None:
    """clear command should delete all done=True todos.

    Issue #4078: Add 'clear' subcommand to batch delete completed todos.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add 3 todos
    for text in ["Task 1", "Task 2", "Task 3"]:
        args = parser.parse_args(["--db", str(db), "add", text])
        run_command(args)
    capsys.readouterr()  # Clear output

    # Mark 2 as done
    run_command(parser.parse_args(["--db", str(db), "done", "1"]))
    run_command(parser.parse_args(["--db", str(db), "done", "2"]))
    capsys.readouterr()  # Clear output

    # Run clear command
    clear_args = parser.parse_args(["--db", str(db), "clear"])
    result = run_command(clear_args)
    assert result == 0, "clear command should succeed"

    captured = capsys.readouterr()
    # Output should show 2 cleared
    assert "Cleared 2 completed todos" in captured.out

    # Verify only 1 pending task remains
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "Task 3" in captured.out
    assert "Task 1" not in captured.out
    assert "Task 2" not in captured.out


def test_cli_clear_no_completed_todos(tmp_path, capsys) -> None:
    """clear command should handle case when no completed todos exist.

    Issue #4078: Clear should output 'No completed todos to clear'.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add 2 todos without marking done
    for text in ["Task 1", "Task 2"]:
        args = parser.parse_args(["--db", str(db), "add", text])
        run_command(args)
    capsys.readouterr()  # Clear output

    # Run clear command
    clear_args = parser.parse_args(["--db", str(db), "clear"])
    result = run_command(clear_args)
    assert result == 0, "clear command should succeed even with no completed todos"

    captured = capsys.readouterr()
    # Output should indicate no completed todos
    assert "No completed todos to clear" in captured.out

    # Verify all tasks still exist
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "Task 1" in captured.out
    assert "Task 2" in captured.out


def test_cli_clear_empty_database(tmp_path, capsys) -> None:
    """clear command should handle empty database gracefully.

    Issue #4078: Clear should work on empty database.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Run clear on empty database
    clear_args = parser.parse_args(["--db", str(db), "clear"])
    result = run_command(clear_args)
    assert result == 0, "clear command should succeed on empty database"

    captured = capsys.readouterr()
    assert "No completed todos to clear" in captured.out

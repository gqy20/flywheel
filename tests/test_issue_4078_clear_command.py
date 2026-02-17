"""Tests for issue #4078: Add 'clear' command to batch delete completed todos."""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_clear_completed_removes_done_todos(tmp_path) -> None:
    """clear_completed() should remove all done=True todos."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add 3 todos
    app.add("task 1")
    app.add("task 2")
    app.add("task 3")

    # Mark 2 as done
    app.mark_done(1)
    app.mark_done(2)

    # Clear completed
    count = app.clear_completed()
    assert count == 2

    # Only task 3 remains
    remaining = app.list()
    assert len(remaining) == 1
    assert remaining[0].id == 3
    assert remaining[0].done is False


def test_clear_completed_returns_zero_when_no_completed(tmp_path) -> None:
    """clear_completed() should return 0 when no todos are completed."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add todos but don't complete any
    app.add("pending 1")
    app.add("pending 2")

    count = app.clear_completed()
    assert count == 0

    # All todos should still be present
    remaining = app.list()
    assert len(remaining) == 2


def test_clear_completed_empty_db(tmp_path) -> None:
    """clear_completed() should return 0 when db is empty."""
    app = TodoApp(str(tmp_path / "db.json"))

    count = app.clear_completed()
    assert count == 0


def test_cli_clear_command_removes_completed(tmp_path, capsys) -> None:
    """CLI 'clear' command should remove all completed todos."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add 3 todos
    args = parser.parse_args(["--db", db, "add", "task 1"])
    assert run_command(args) == 0
    args = parser.parse_args(["--db", db, "add", "task 2"])
    assert run_command(args) == 0
    args = parser.parse_args(["--db", db, "add", "task 3"])
    assert run_command(args) == 0

    # Mark 2 as done
    args = parser.parse_args(["--db", db, "done", "1"])
    assert run_command(args) == 0
    args = parser.parse_args(["--db", db, "done", "2"])
    assert run_command(args) == 0

    # Run clear
    args = parser.parse_args(["--db", db, "clear"])
    assert run_command(args) == 0

    captured = capsys.readouterr()
    assert "Cleared 2 completed todos" in captured.out


def test_cli_clear_no_completed_todos(tmp_path, capsys) -> None:
    """CLI 'clear' command should report when no completed todos exist."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add todos but don't complete any
    args = parser.parse_args(["--db", db, "add", "pending"])
    assert run_command(args) == 0

    # Run clear
    args = parser.parse_args(["--db", db, "clear"])
    assert run_command(args) == 0

    captured = capsys.readouterr()
    assert "No completed todos to clear" in captured.out

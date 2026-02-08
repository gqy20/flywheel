"""Tests for issue #2236: list command --pending flag behavior."""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_list_without_pending_flag_shows_all(tmp_path, capsys) -> None:
    """Issue #2236: list command without --pending flag should show all todos."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add todos
    app.add("pending task")
    app.add("completed task")
    app.mark_done(2)

    # Run list command without --pending flag
    parser = build_parser()
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0

    out = capsys.readouterr().out
    # Both pending and completed todos should be shown
    assert "pending task" in out
    assert "completed task" in out


def test_cli_list_with_pending_flag_shows_only_pending(tmp_path, capsys) -> None:
    """Issue #2236: list command with --pending flag should show only pending todos."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add todos
    app.add("pending task 1")
    app.add("completed task")
    app.add("pending task 2")
    app.mark_done(2)

    # Run list command with --pending flag
    parser = build_parser()
    args = parser.parse_args(["--db", db, "list", "--pending"])
    assert run_command(args) == 0

    out = capsys.readouterr().out
    # Only pending todos should be shown
    assert "pending task 1" in out
    assert "pending task 2" in out
    assert "completed task" not in out


def test_cli_list_pending_with_all_completed_todos(tmp_path, capsys) -> None:
    """Issue #2236: list command with --pending flag when all todos are completed."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add and complete all todos
    app.add("task 1")
    app.add("task 2")
    app.mark_done(1)
    app.mark_done(2)

    # Run list command with --pending flag
    parser = build_parser()
    args = parser.parse_args(["--db", db, "list", "--pending"])
    assert run_command(args) == 0

    out = capsys.readouterr().out
    # Should show no pending todos
    assert "task 1" not in out
    assert "task 2" not in out


def test_cli_list_pending_with_empty_list(tmp_path, capsys) -> None:
    """Issue #2236: list command with --pending flag on empty todo list."""
    db = str(tmp_path / "db.json")

    # Run list command with --pending flag on empty database
    parser = build_parser()
    args = parser.parse_args(["--db", db, "list", "--pending"])
    assert run_command(args) == 0

    out = capsys.readouterr().out
    # Should handle empty list gracefully
    assert "Error" not in out


def test_app_list_show_all_false_filters_completed(tmp_path) -> None:
    """Issue #2236: TodoApp.list(show_all=False) should filter out completed todos."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add todos
    app.add("pending 1")
    app.add("done 1")
    app.add("pending 2")
    app.add("done 2")
    app.mark_done(2)
    app.mark_done(4)

    # show_all=True should return all todos
    all_todos = app.list(show_all=True)
    assert len(all_todos) == 4

    # show_all=False should return only pending todos
    pending_todos = app.list(show_all=False)
    assert len(pending_todos) == 2
    assert all(not todo.done for todo in pending_todos)
    assert pending_todos[0].text == "pending 1"
    assert pending_todos[1].text == "pending 2"

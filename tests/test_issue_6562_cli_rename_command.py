"""Regression tests for issue #6562: CLI missing 'rename' command."""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_exists() -> None:
    """CLI should have a 'rename' subparser defined."""
    parser = build_parser()
    # This will raise if 'rename' is not a valid command
    args = parser.parse_args(["rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_updates_todo_text(tmp_path, capsys) -> None:
    """Running 'todo rename 1 renamed' should update todo.text and todo.updated_at."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "renamed"])
    assert run_command(args) == 0

    # Verify output
    captured = capsys.readouterr()
    assert "renamed" in captured.out

    # Verify the text was actually updated
    app = TodoApp(db)
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed"


def test_cli_rename_nonexistent_todo_returns_error(tmp_path, capsys) -> None:
    """Running 'todo rename 999 x' should return exit code 1 with 'Todo #999 not found' error."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename a non-existent todo
    args = parser.parse_args(["--db", db, "rename", "999", "x"])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_empty_text_returns_error(tmp_path, capsys) -> None:
    """Running 'todo rename 1 \"\"' should return exit code 1 with 'Todo text cannot be empty' error."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "test"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "cannot be empty" in captured.out or "cannot be empty" in captured.err

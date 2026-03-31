"""Regression tests for Issue #6841: CLI does not expose 'rename' command.

This test file ensures that the CLI exposes a 'rename' command that calls
the existing Todo.rename() method.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_exists() -> None:
    """The 'rename' subcommand should be recognized by the parser."""
    parser = build_parser()
    # Should not raise - rename command should be valid
    args = parser.parse_args(["--db", ".test.json", "rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """rename command should successfully rename a todo and return exit code 0."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "renamed todo"])

    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out

    # Verify the rename persisted
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed todo"


def test_cli_rename_command_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """rename command should return exit code 1 when todo not found."""
    db = str(tmp_path / "cli.json")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_rejects_empty_text(tmp_path, capsys) -> None:
    """rename command should return exit code 1 for empty text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_cli_rename_command_rejects_whitespace_only_text(tmp_path, capsys) -> None:
    """rename command should return exit code 1 for whitespace-only text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "   "])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_app_rename_method_exists(tmp_path) -> None:
    """TodoApp should have a rename method that works correctly."""
    app = TodoApp(str(tmp_path / "db.json"))
    app.add("original")

    renamed = app.rename(1, "renamed")
    assert renamed.text == "renamed"

    # Verify persistence
    todos = app.list()
    assert todos[0].text == "renamed"


def test_app_rename_raises_for_missing_todo(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for non-existent todo."""
    app = TodoApp(str(tmp_path / "db.json"))

    try:
        app.rename(99, "new text")
        raise AssertionError("Expected ValueError for missing todo")
    except ValueError as e:
        assert "not found" in str(e).lower()

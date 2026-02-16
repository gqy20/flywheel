"""Regression tests for Issue #3834: CLI does not expose Todo.rename() functionality.

This test file ensures that the CLI supports the 'rename' subcommand to expose
Todo.rename() through the command-line interface.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_with_valid_id_returns_exit_code_0(tmp_path, capsys) -> None:
    """CLI rename with valid ID should return exit code 0."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])

    result = run_command(args)
    assert result == 0, "rename with valid ID should return 0"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "new text" in captured.out


def test_cli_rename_with_invalid_id_returns_exit_code_1(tmp_path, capsys) -> None:
    """CLI rename with invalid ID should return exit code 1."""
    db = str(tmp_path / "db.json")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "999", "new text"])

    result = run_command(args)
    assert result == 1, "rename with invalid ID should return 1"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_with_empty_text_returns_exit_code_1(tmp_path, capsys) -> None:
    """CLI rename with empty text should return exit code 1."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])

    result = run_command(args)
    assert result == 1, "rename with empty text should return 1"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_updates_todo_text(tmp_path) -> None:
    """CLI rename should actually update the todo's text."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "updated text"])

    result = run_command(args)
    assert result == 0

    # Verify the text was actually changed
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "updated text"


def test_cli_rename_strips_whitespace(tmp_path, capsys) -> None:
    """CLI rename should strip whitespace from new text like other commands."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "  padded text  "])

    result = run_command(args)
    assert result == 0

    # Verify whitespace was stripped
    todos = app.list()
    assert todos[0].text == "padded text"

"""Regression test for issue #5084: CLI rename command."""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """CLI 'rename' subcommand should update todo text via Todo.rename()."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out

    # Verify the rename persisted
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    out = capsys.readouterr().out
    assert "new text" in out
    assert "original text" not in out


def test_cli_rename_command_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """CLI 'rename' should return error code 1 for non-existent todo."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """CLI 'rename' should return error code 1 with empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "original"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "cannot be empty" in captured.out or "cannot be empty" in captured.err


def test_app_rename_method(tmp_path) -> None:
    """TodoApp.rename() should call Todo.rename() and persist changes."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original")
    assert added.id == 1

    renamed = app.rename(1, "renamed text")
    assert renamed.text == "renamed text"

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed text"

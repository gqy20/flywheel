"""Tests for issue #7010: CLI missing 'rename' subcommand.

Bug: CLI missing 'rename' subcommand - Todo.rename() method exists in model but is not exposed via CLI
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_exists(tmp_path, capsys) -> None:
    """CLI should have a 'rename' subcommand."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "renamed task"])
    assert run_command(args) == 0

    # Verify the rename was successful
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "renamed task" in captured.out


def test_cli_rename_command_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """CLI rename should return error for non-existent todo."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "999", "new text"])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_rejects_empty_text(tmp_path, capsys) -> None:
    """CLI rename should reject empty text after strip."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_cli_rename_command_sanitizes_output(tmp_path, capsys) -> None:
    """CLI rename should sanitize output text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original"])
    assert run_command(args) == 0

    # Rename with text containing control characters
    args = parser.parse_args(["--db", db, "rename", "1", "text\nwith\x1b[31m"])
    assert run_command(args) == 0

    # Verify output is sanitized (no raw control chars in output)
    captured = capsys.readouterr()
    assert "\x1b" not in captured.out
    assert "\n" not in captured.out or "text" in captured.out


def test_app_rename_method_exists(tmp_path) -> None:
    """TodoApp should have a rename method."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original")
    assert added.id == 1

    # Rename should work
    renamed = app.rename(1, "new text")
    assert renamed.text == "new text"

    # Verify persistence
    todos = app.list()
    assert todos[0].text == "new text"


def test_app_rename_rejects_empty_text(tmp_path) -> None:
    """TodoApp.rename should reject empty text."""
    app = TodoApp(str(tmp_path / "db.json"))
    app.add("original")

    import pytest
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(1, "")


def test_app_rename_raises_for_missing_todo(tmp_path) -> None:
    """TodoApp.rename should raise for non-existent todo."""
    app = TodoApp(str(tmp_path / "db.json"))

    import pytest
    with pytest.raises(ValueError, match="Todo #999 not found"):
        app.rename(999, "new text")

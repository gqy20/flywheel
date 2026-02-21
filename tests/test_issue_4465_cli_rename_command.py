"""Tests for issue #4465: CLI rename command."""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """Issue #4465: CLI should support rename command to update todo text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "renamed task"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "renamed task" in captured.out

    # Verify the text was updated via list
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    out = capsys.readouterr().out
    assert "renamed task" in out


def test_cli_rename_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """Issue #4465: rename should return error for non-existent ID."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err or "not found" in captured.out


def test_cli_rename_empty_text_returns_error(tmp_path, capsys) -> None:
    """Issue #4465: rename should return error for empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "cannot be empty" in captured.err or "cannot be empty" in captured.out


def test_app_rename_method(tmp_path) -> None:
    """Issue #4465: TodoApp should expose rename method."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original text")
    assert added.id == 1
    assert app.list()[0].text == "original text"

    renamed = app.rename(1, "new text")
    assert renamed.id == 1
    assert renamed.text == "new text"
    assert app.list()[0].text == "new text"


def test_app_rename_nonexistent_raises_error(tmp_path) -> None:
    """Issue #4465: TodoApp.rename should raise error for non-existent ID."""
    app = TodoApp(str(tmp_path / "db.json"))

    import pytest

    with pytest.raises(ValueError, match="not found"):
        app.rename(99, "new text")

"""Tests for CLI rename command - Issue #3545."""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """Test that 'todo rename 1 new text' successfully renames todo #1."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    # Test rename command
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    assert run_command(args) == 0

    # Verify output
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "new text" in captured.out

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_cli_rename_command_nonexistent_id(tmp_path, capsys) -> None:
    """Test that 'todo rename 99 text' with non-existent ID returns error code 1."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "99", "some text"])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_empty_text(tmp_path, capsys) -> None:
    """Test that 'todo rename 1 ""' with empty text returns error code 1."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "cannot be empty" in captured.out or "cannot be empty" in captured.err

    # Verify original text is unchanged
    todos = app.list()
    assert todos[0].text == "original text"

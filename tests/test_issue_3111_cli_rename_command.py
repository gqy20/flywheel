"""Tests for CLI rename command (issue #3111)."""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_has_rename_subcommand() -> None:
    """CLI should support 'rename' subcommand in build_parser()."""
    parser = build_parser()
    # Parse help to see available subcommands
    help_text = parser.format_help()
    assert "rename" in help_text, "CLI should have 'rename' subcommand"


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """CLI 'rename' command should update todo text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "old text"])
    assert run_command(args) == 0

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "new text" in captured.out


def test_cli_rename_command_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """CLI rename command should return error for non-existent todo ID."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "not found" in captured.err or "not found" in captured.out


def test_cli_rename_command_rejects_empty_text(tmp_path, capsys) -> None:
    """CLI rename command should reject empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "some text"])
    assert run_command(args) == 0
    capsys.readouterr()  # Clear output

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_todoapp_has_rename_method() -> None:
    """TodoApp should have a rename() method that updates todo text."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        from pathlib import Path

        db = str(Path(tmp_dir) / "test.json")
        app = TodoApp(db)

        # Add a todo
        app.add("original text")

        # Rename it using the app's rename method
        todo = app.rename(1, "updated text")
        assert todo.text == "updated text"

        # Verify the change persisted
        todos = app.list()
        assert todos[0].text == "updated text"

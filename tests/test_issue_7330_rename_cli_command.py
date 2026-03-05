"""Regression tests for Issue #7330: Missing 'rename' command in CLI.

This test file ensures that the CLI exposes a 'rename' command that calls
Todo.rename() functionality.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_has_rename_subparser() -> None:
    """The CLI should have a 'rename' subparser defined."""
    parser = build_parser()
    # Try parsing a rename command - this will raise if the subparser doesn't exist
    args = parser.parse_args(["rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """Running 'todo rename 1 new text' should successfully update todo text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # First add a todo
    app.add("original text")

    # Now rename it via CLI
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "updated text"])
    result = run_command(args)

    assert result == 0, "rename command should return 0 on success"
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out or "renamed" in captured.out.lower()

    # Verify the text was actually updated
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "updated text"


def test_cli_rename_command_sanitizes_output(tmp_path, capsys) -> None:
    """Rename command should sanitize output with _sanitize_text()."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo with control characters
    app.add("original")

    # Rename to text with control characters
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "text with \x1b[31mcontrol\x1b[0m"])
    result = run_command(args)

    assert result == 0
    captured = capsys.readouterr()
    # Output should not contain raw ANSI escape sequences
    assert "\x1b" not in captured.out


def test_cli_rename_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """Attempting to rename non-existent ID should return exit code 1."""
    db = str(tmp_path / "cli.json")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "999", "new text"])
    result = run_command(args)

    assert result == 1, "rename command should return 1 for non-existent ID"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_app_rename_method_exists() -> None:
    """TodoApp should have a rename method for CLI to call."""
    db = "/tmp/test.json"
    app = TodoApp(db)
    assert hasattr(app, "rename"), "TodoApp should have a rename method"


def test_app_rename_updates_todo(tmp_path) -> None:
    """TodoApp.rename() should update todo text."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    added = app.add("original")
    assert added.id == 1

    renamed = app.rename(1, "new text")
    assert renamed.text == "new text"

    # Verify persistence
    todos = app.list()
    assert todos[0].text == "new text"


def test_app_rename_nonexistent_raises_error(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent ID."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    try:
        app.rename(999, "new text")
        raise AssertionError("Expected ValueError for non-existent ID")
    except ValueError as e:
        assert "not found" in str(e).lower()

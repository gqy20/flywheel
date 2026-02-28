"""Regression tests for Issue #6214: CLI missing 'rename' command.

This test file ensures that the CLI has a 'rename' command that uses
the existing Todo.rename() method from the domain model.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_has_rename_subparser() -> None:
    """The CLI should have a 'rename' subparser defined."""
    parser = build_parser()
    # Parse the rename command with required arguments
    args = parser.parse_args(["rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_renames_todo(tmp_path, capsys) -> None:
    """The CLI 'rename' command should successfully rename a todo."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    added = app.add("original text")
    assert added.id == 1
    assert added.text == "original text"

    # Use CLI to rename it
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "renamed text"])
    result = run_command(args)

    assert result == 0, "rename command should return 0 on success"

    # Verify the rename worked
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed text"

    # Verify output message
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out


def test_cli_rename_command_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """The CLI 'rename' command should return error for non-existent todo."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)

    assert result == 1, "rename command should return 1 on error"
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_validates_text(tmp_path, capsys) -> None:
    """The CLI 'rename' command should validate the new text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)

    assert result == 1, "rename command should return 1 for empty text"
    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_app_rename_method_exists() -> None:
    """TodoApp should have a rename method."""
    app = TodoApp()
    assert hasattr(app, "rename"), "TodoApp should have a rename method"
    assert callable(getattr(app, "rename"))


def test_app_rename_method_works(tmp_path) -> None:
    """TodoApp.rename() should rename a todo and persist the change."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo
    added = app.add("original")
    assert added.id == 1

    # Rename it
    renamed = app.rename(1, "renamed")
    assert renamed.text == "renamed"
    assert renamed.id == 1

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed"


def test_app_rename_raises_for_missing_todo(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent todo."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Try to rename a non-existent todo
    import pytest

    with pytest.raises(ValueError, match="not found"):
        app.rename(99, "new text")

"""Regression tests for Issue #3111: CLI缺少rename子命令.

This test file ensures that the CLI exposes the rename functionality
that already exists in the Todo data model and TodoApp should have.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_subcommand_exists() -> None:
    """build_parser should include a rename subcommand."""
    parser = build_parser()
    # This will raise if 'rename' is not a valid subcommand
    args = parser.parse_args(["rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_returns_0_on_success(tmp_path, capsys) -> None:
    """rename command should return 0 and update todo text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "old text"])
    assert run_command(args) == 0

    # Then rename it
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    assert run_command(args) == 0

    # Verify the text was changed
    out = capsys.readouterr()
    assert "Renamed" in out.out or "renamed" in out.out.lower()


def test_cli_rename_returns_1_for_missing_todo(tmp_path, capsys) -> None:
    """rename command should return 1 for non-existent todo ID."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename a non-existent todo
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_app_rename_method_exists() -> None:
    """TodoApp should have a rename method."""
    app = TodoApp()
    assert hasattr(app, "rename"), "TodoApp should have a rename method"


def test_app_rename_updates_todo_text(tmp_path) -> None:
    """TodoApp.rename should update todo text and persist changes."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("original text")
    assert added.text == "original text"

    # Rename it
    renamed = app.rename(added.id, "renamed text")
    assert renamed.text == "renamed text"

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed text"


def test_app_rename_raises_for_missing_todo(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for non-existent ID."""
    app = TodoApp(str(tmp_path / "db.json"))

    try:
        app.rename(999, "new text")
        raise AssertionError("Expected ValueError for non-existent todo")
    except ValueError as e:
        assert "not found" in str(e).lower()

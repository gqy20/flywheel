"""Regression tests for Issue #6053: CLI missing rename command.

This test file ensures that the CLI exposes the Todo.rename() functionality
through a 'rename' subcommand.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_has_rename_subcommand(tmp_path, capsys) -> None:
    """CLI should support 'rename' subcommand."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    assert run_command(args) == 0

    # Clear previous output
    capsys.readouterr()

    # Verify the rename took effect
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    out = capsys.readouterr().out
    assert "new text" in out
    assert "original text" not in out


def test_cli_rename_updates_updated_at_timestamp(tmp_path) -> None:
    """Rename should update the updated_at timestamp."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo
    todo = app.add("original")
    original_updated_at = todo.updated_at

    # Rename via TodoApp
    renamed = app.rename(1, "renamed")
    assert renamed.text == "renamed"
    assert renamed.updated_at >= original_updated_at


def test_cli_rename_validates_non_empty_text(tmp_path, capsys) -> None:
    """Rename command should reject empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original"])
    assert run_command(args) == 0

    # Attempt to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)

    # Should return error code 1
    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """Rename command should return error for non-existent todo ID."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Attempt to rename non-existent todo
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)

    # Should return error code 1
    assert result == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_app_rename_method_exists() -> None:
    """TodoApp should have a rename method."""
    app = TodoApp()
    assert hasattr(app, "rename"), "TodoApp should have a 'rename' method"


def test_app_rename_returns_updated_todo(tmp_path) -> None:
    """TodoApp.rename() should return the updated todo."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo
    app.add("original")

    # Rename should return the updated todo
    renamed = app.rename(1, "renamed")
    assert renamed.id == 1
    assert renamed.text == "renamed"


def test_app_rename_raises_for_nonexistent_id(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent ID."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Attempt to rename non-existent todo
    try:
        app.rename(99, "new text")
        raise AssertionError("Expected ValueError for non-existent todo ID")
    except ValueError as e:
        assert "not found" in str(e).lower()

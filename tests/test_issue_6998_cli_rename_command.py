"""Regression tests for Issue #6998: Add CLI 'rename' command.

This test file ensures that the CLI exposes Todo.rename() functionality
via a 'rename' subcommand.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_with_valid_id_and_text(tmp_path, capsys) -> None:
    """'todo rename 1 new text' should successfully rename todo #1."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    # Rename via CLI
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    result = run_command(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "new text" in captured.out

    # Verify the rename persisted
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_cli_rename_with_invalid_id_returns_error(tmp_path, capsys) -> None:
    """'todo rename 99 x' should return error for non-existent id."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo (id=1)
    app.add("existing")

    # Try to rename non-existent todo
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_with_empty_text_returns_error(tmp_path, capsys) -> None:
    """'todo rename 1 ""' should return error for empty text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    # Try to rename with empty text
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_app_rename_method_works(tmp_path) -> None:
    """TodoApp.rename() should work correctly."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    app.add("original")
    assert app.list()[0].text == "original"

    # Rename it
    renamed = app.rename(1, "renamed")
    assert renamed.text == "renamed"
    assert renamed.id == 1

    # Verify persistence
    assert app.list()[0].text == "renamed"


def test_app_rename_raises_for_nonexistent_id(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent id."""
    app = TodoApp(str(tmp_path / "db.json"))

    try:
        app.rename(99, "new text")
        raise AssertionError("Expected ValueError for non-existent id")
    except ValueError as e:
        assert "not found" in str(e).lower()


def test_app_rename_raises_for_empty_text(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for empty text."""
    app = TodoApp(str(tmp_path / "db.json"))
    app.add("original")

    try:
        app.rename(1, "")
        raise AssertionError("Expected ValueError for empty text")
    except ValueError as e:
        assert "empty" in str(e).lower()

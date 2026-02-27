"""Regression tests for Issue #6082: Expose rename method in CLI.

This test file ensures that the CLI exposes an 'edit' subcommand that allows
users to edit todo text via the Todo.rename() method.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_has_edit_subcommand() -> None:
    """CLI should have an 'edit' subcommand."""
    parser = build_parser()
    args = parser.parse_args(["edit", "1", "new text"])
    assert args.command == "edit"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_edit_command_updates_todo_text(tmp_path, capsys) -> None:
    """Running 'edit' should update the todo text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Edit the todo
    args = parser.parse_args(["--db", db, "edit", "1", "new text"])
    result = run_command(args)
    assert result == 0

    # Verify the text was updated
    captured = capsys.readouterr()
    assert "Edited" in captured.out or "updated" in captured.out.lower()
    assert "new text" in captured.out

    # Verify by listing
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "original text" not in captured.out


def test_cli_edit_command_updates_timestamp(tmp_path) -> None:
    """Running 'edit' should update the updated_at timestamp."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo
    todo = app.add("original text")
    original_updated_at = todo.updated_at

    # Edit the todo via CLI
    parser = build_parser()
    args = parser.parse_args(["--db", db, "edit", "1", "new text"])
    result = run_command(args)
    assert result == 0

    # Verify timestamp was updated
    todos = app.list()
    assert todos[0].updated_at >= original_updated_at


def test_cli_edit_command_shows_error_for_nonexistent_todo(tmp_path, capsys) -> None:
    """Editing a non-existent todo should show an error."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "edit", "99", "new text"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out.lower() or "not found" in captured.err.lower()


def test_cli_edit_command_shows_error_for_empty_text(tmp_path, capsys) -> None:
    """Editing with empty text should show an error."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Try to edit with empty text
    args = parser.parse_args(["--db", db, "edit", "1", ""])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_app_rename_method(tmp_path) -> None:
    """TodoApp should have a rename method that calls Todo.rename()."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("original text")
    assert added.id == 1
    original_updated_at = added.updated_at

    # Rename via app method
    renamed = app.rename(1, "new text")
    assert renamed.text == "new text"
    assert renamed.updated_at >= original_updated_at

    # Verify persistence
    todos = app.list()
    assert todos[0].text == "new text"


def test_app_rename_shows_error_for_nonexistent_todo(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent todo."""
    app = TodoApp(str(tmp_path / "db.json"))

    try:
        app.rename(99, "new text")
        raise AssertionError("Expected ValueError for non-existent todo")
    except ValueError as e:
        assert "not found" in str(e).lower()

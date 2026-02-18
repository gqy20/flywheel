"""Regression tests for Issue #4231: Add edit/rename command to CLI.

This test file ensures that the CLI supports an 'edit' subcommand that
calls Todo.rename() via TodoApp, following the same pattern as done/undone.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_app_edit_updates_todo_text(tmp_path) -> None:
    """TodoApp.edit() should update todo text via Todo.rename()."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("original text")
    assert added.text == "original text"
    original_updated_at = added.updated_at

    # Edit the todo
    edited = app.edit(added.id, "new text")
    assert edited.text == "new text"
    assert edited.updated_at >= original_updated_at


def test_app_edit_raises_error_for_nonexistent_todo(tmp_path) -> None:
    """TodoApp.edit() should raise ValueError for non-existent todo."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Try to edit non-existent todo
    try:
        app.edit(999, "new text")
        raise AssertionError("Expected ValueError for non-existent todo")
    except ValueError as e:
        assert "not found" in str(e).lower()


def test_app_edit_raises_error_for_empty_text(tmp_path) -> None:
    """TodoApp.edit() should raise ValueError for empty text."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("original")

    # Try to edit with empty text
    try:
        app.edit(added.id, "")
        raise AssertionError("Expected ValueError for empty text")
    except ValueError as e:
        assert "empty" in str(e).lower()


def test_cli_edit_command_updates_todo(tmp_path, capsys) -> None:
    """CLI edit command should update todo text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Edit the todo
    args = parser.parse_args(["--db", db, "edit", "1", "new text"])
    result = run_command(args)
    assert result == 0

    # Verify output
    captured = capsys.readouterr()
    assert "Edited" in captured.out or "updated" in captured.out.lower()
    assert "#1" in captured.out

    # Verify the text was actually changed
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "original text" not in captured.out


def test_cli_edit_command_shows_error_for_missing_todo(tmp_path, capsys) -> None:
    """CLI edit command should show error for non-existent todo."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "edit", "999", "new text"])
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out.lower() or "not found" in captured.err.lower()


def test_cli_edit_command_shows_error_for_empty_text(tmp_path, capsys) -> None:
    """CLI edit command should show error for empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "original"])
    assert run_command(args) == 0

    # Try to edit with empty text
    args = parser.parse_args(["--db", db, "edit", "1", ""])
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_cli_edit_command_strips_whitespace(tmp_path, capsys) -> None:
    """CLI edit command should strip whitespace from text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo
    args = parser.parse_args(["--db", db, "add", "original"])
    assert run_command(args) == 0

    # Edit with padded text
    args = parser.parse_args(["--db", db, "edit", "1", "  padded  "])
    result = run_command(args)
    assert result == 0

    # Verify the text was stripped
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "padded" in captured.out

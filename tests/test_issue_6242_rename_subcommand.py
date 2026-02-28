"""Regression tests for Issue #6242: CLI missing 'rename' subcommand.

This test file ensures that the CLI supports the 'rename' subcommand
that calls the existing Todo.rename() method.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_subcommand_exists() -> None:
    """The 'rename' subcommand should be registered in the parser."""
    parser = build_parser()
    # This should not raise an error - if rename is missing, parse_args will fail
    args = parser.parse_args(["rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_todo_success(tmp_path, capsys) -> None:
    """'todo rename <id> <text>' should successfully rename a todo."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    # Rename via CLI
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "renamed text"])
    result = run_command(args)

    assert result == 0, "rename should return exit code 0 on success"

    # Verify the text was changed
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed text"

    # Check output message
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out


def test_cli_rename_todo_not_found(tmp_path, capsys) -> None:
    """'todo rename <id> <text>' should return exit code 1 when todo not found."""
    db = str(tmp_path / "db.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)

    assert result == 1, "rename should return exit code 1 when todo not found"

    captured = capsys.readouterr()
    assert "not found" in captured.out.lower() or "not found" in captured.err.lower()


def test_cli_rename_with_empty_text_raises_error(tmp_path, capsys) -> None:
    """'todo rename' with empty text should raise validation error."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)

    assert result == 1, "rename with empty text should return exit code 1"

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_cli_rename_with_whitespace_only_text_raises_error(tmp_path, capsys) -> None:
    """'todo rename' with whitespace-only text should raise validation error."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "   "])
    result = run_command(args)

    assert result == 1, "rename with whitespace-only text should return exit code 1"

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_app_rename_method_exists() -> None:
    """TodoApp should have a rename method that calls Todo.rename()."""
    app = TodoApp(":memory:")
    assert hasattr(app, "rename"), "TodoApp should have a 'rename' method"


def test_app_rename_updates_todo_text(tmp_path) -> None:
    """TodoApp.rename() should update the todo text and persist changes."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    # Rename using the app method
    todo = app.rename(1, "renamed text")

    assert todo.text == "renamed text"

    # Verify persistence by loading fresh
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed text"


def test_app_rename_not_found_raises_error(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError when todo not found."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    import pytest

    with pytest.raises(ValueError, match="not found"):
        app.rename(99, "new text")


def test_app_rename_empty_text_raises_error(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for empty text."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    app.add("original")

    import pytest

    with pytest.raises(ValueError, match="cannot be empty"):
        app.rename(1, "")

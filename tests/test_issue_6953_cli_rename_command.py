"""Regression tests for Issue #6953: CLI missing 'rename' command.

This test file ensures that the CLI has a 'rename' subcommand that allows
updating the text of an existing todo item.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_has_rename_subcommand() -> None:
    """The CLI parser should include a 'rename' subcommand."""
    parser = build_parser()
    # Parse the rename command - should not raise an error
    args = parser.parse_args(["rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """Running 'todo rename <id> <text>' should update the todo's text."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo first
    todo = app.add("original text")
    assert todo.text == "original text"

    # Use CLI to rename it
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "updated text"])
    result = run_command(args)

    assert result == 0, "rename command should succeed"

    # Verify the text was updated
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "updated text"


def test_cli_rename_command_outputs_success_message(tmp_path, capsys) -> None:
    """Rename command should output a success message."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)
    app.add("original")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "new"])
    result = run_command(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "Renamed" in captured.out or "rename" in captured.out.lower()
    assert "#1" in captured.out


def test_cli_rename_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """Rename command with non-existent ID should return error code 1."""
    db = str(tmp_path / "db.json")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "999", "new text"])
    result = run_command(args)

    assert result == 1, "rename with non-existent ID should return error code 1"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """Rename command with empty text should return error code 1."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)
    app.add("original")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)

    assert result == 1, "rename with empty text should return error code 1"
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_app_rename_method_exists_and_works(tmp_path) -> None:
    """TodoApp should have a rename method that updates todo text."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo
    app.add("original text")

    # Rename it using the app method
    todo = app.rename(1, "new text")

    assert todo.text == "new text"
    assert todo.id == 1

    # Verify persistence
    todos = app.list()
    assert todos[0].text == "new text"


def test_app_rename_raises_for_nonexistent_id(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for non-existent ID."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    try:
        app.rename(999, "new text")
        raise AssertionError("Expected ValueError for non-existent ID")
    except ValueError as e:
        assert "not found" in str(e).lower()


def test_app_rename_raises_for_empty_text(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for empty text."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)
    app.add("original")

    try:
        app.rename(1, "")
        raise AssertionError("Expected ValueError for empty text")
    except ValueError as e:
        assert "empty" in str(e).lower()

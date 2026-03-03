"""Regression tests for Issue #6953: CLI missing 'rename' command.

This test file ensures that the CLI exposes a 'rename' subcommand that
calls the existing Todo.rename() method from the data model.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """The 'rename' subcommand should update todo text.

    Given: A todo with id=1 and text="original"
    When: User runs 'todo rename 1 new text'
    Then: Todo text should be updated to "new text"
    """
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    app.add("original task")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])

    result = run_command(args)
    assert result == 0, "rename command should return 0 on success"

    # Verify text was updated
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"

    # Verify output message
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out


def test_cli_rename_command_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """The 'rename' subcommand should return error for non-existent ID.

    Given: An empty database
    When: User runs 'todo rename 999 some text'
    Then: Should return error code 1 with 'not found' message
    """
    db = str(tmp_path / "cli.json")
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "999", "some text"])

    result = run_command(args)
    assert result == 1, "rename command should return 1 for missing todo"

    captured = capsys.readouterr()
    assert "not found" in captured.out.lower() or "not found" in captured.err.lower()


def test_cli_rename_command_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """The 'rename' subcommand should validate empty text.

    Given: A todo with id=1
    When: User runs 'todo rename 1 ""'
    Then: Should return error code 1 with validation message
    """
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    app.add("original task")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])

    result = run_command(args)
    assert result == 1, "rename command should return 1 for empty text"

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()

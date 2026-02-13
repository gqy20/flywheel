"""Regression tests for Issue #2992: Add rename command to CLI.

This test file ensures that users can rename todo items via the CLI using
the 'todo rename <id> <new_text>' command.

Issue #2992 acceptance criteria:
- User can rename todo via 'todo rename <id> <new_text>' command
- updated_at is automatically updated after rename
- Empty text triggers an error message
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """rename command should update the todo text.

    Issue #2992: Users should be able to rename todo items via CLI.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename the todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Updated task"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "Updated task" in captured.out

    # Verify the todo was actually renamed
    app = TodoApp(db_path=str(db))
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "Updated task"


def test_cli_rename_command_updates_updated_at_timestamp(tmp_path, capsys) -> None:
    """rename command should update the updated_at timestamp.

    Issue #2992: The updated_at field should be automatically updated after rename.
    """
    import time

    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo and capture its initial updated_at
    add_args = parser.parse_args(["--db", str(db), "add", "Task to rename"])
    run_command(add_args)
    capsys.readouterr()

    app = TodoApp(db_path=str(db))
    initial_updated_at = app.list()[0].updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    # Rename the todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Renamed task"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"
    capsys.readouterr()

    # Verify updated_at changed
    renamed_todo = app.list()[0]
    assert renamed_todo.updated_at != initial_updated_at


def test_cli_rename_command_rejects_empty_text(tmp_path, capsys) -> None:
    """rename command should reject empty text with an error.

    Issue #2992: Empty text should trigger an error message.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail with empty text"

    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "empty" in captured.err.lower()


def test_cli_rename_command_rejects_whitespace_only_text(tmp_path, capsys) -> None:
    """rename command should reject whitespace-only text with an error.

    Issue #2992: Whitespace-only text should also trigger an error message.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with whitespace-only text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "   "])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail with whitespace-only text"

    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "empty" in captured.err.lower()


def test_cli_rename_command_error_for_nonexistent_todo(tmp_path, capsys) -> None:
    """rename command should report error for non-existent todo.

    Issue #2992: Renaming a non-existent todo should fail gracefully.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to rename a todo that doesn't exist
    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "New text"])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail for non-existent todo"

    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "not found" in captured.err


def test_app_rename_method_exists() -> None:
    """TodoApp should have a rename method.

    Issue #2992: TodoApp needs a rename method for CLI to call.
    """
    app = TodoApp()
    assert hasattr(app, "rename")
    assert callable(app.rename)

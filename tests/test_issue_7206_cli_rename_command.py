"""Regression tests for Issue #7206: CLI missing rename command.

The Todo class has a rename() method, but the CLI does not expose it.
This test file ensures the CLI rename command works correctly.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_run_command_rename(tmp_path, capsys) -> None:
    """CLI should support 'rename' command to update todo text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    parser = build_parser()

    # First add a todo
    added = app.add("original text")
    todo_id = added.id

    # Now test the rename command
    args = parser.parse_args(["--db", db, "rename", str(todo_id), "new text"])
    result = run_command(args)

    assert result == 0, "rename command should return 0 on success"

    # Verify output format
    captured = capsys.readouterr()
    assert f"Renamed #{todo_id}" in captured.out
    assert "new text" in captured.out

    # Verify the todo was actually renamed
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_cli_rename_not_found(tmp_path, capsys) -> None:
    """CLI rename command should return error code 1 for non-existent todo."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)

    assert result == 1, "rename command should return 1 when todo not found"

    captured = capsys.readouterr()
    assert "not found" in captured.out.lower() or "not found" in captured.err.lower()


def test_cli_rename_strips_whitespace(tmp_path, capsys) -> None:
    """CLI rename command should strip whitespace from new text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    parser = build_parser()

    added = app.add("original")
    todo_id = added.id

    args = parser.parse_args(["--db", db, "rename", str(todo_id), "  padded text  "])
    result = run_command(args)

    assert result == 0

    # Verify text was stripped
    todos = app.list()
    assert todos[0].text == "padded text"


def test_app_rename_method(tmp_path) -> None:
    """TodoApp should have a rename method that works correctly."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original")
    renamed = app.rename(added.id, "renamed")

    assert renamed.text == "renamed"
    assert renamed.id == added.id

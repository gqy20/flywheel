"""Regression tests for Issue #6479: TodoApp 缺少 rename 功能的 CLI 命令入口.

This test file ensures that the CLI supports the 'rename' command to rename
existing todos via the command line interface.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """CLI rename command should successfully rename an existing todo."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    todo = app.add("original task")

    # Use CLI to rename it
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", str(todo.id), "new task"])
    result = run_command(args)

    assert result == 0
    captured = capsys.readouterr()
    assert f"Renamed #{todo.id}" in captured.out
    assert "new task" in captured.out

    # Verify the todo was actually renamed
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new task"


def test_cli_rename_command_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """CLI rename command should return error for non-existent todo ID."""
    db = str(tmp_path / "cli.json")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "999", "new text"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_command_empty_text_returns_error(tmp_path, capsys) -> None:
    """CLI rename command should return error for empty text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    todo = app.add("original task")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", str(todo.id), ""])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_app_rename_method_exists(tmp_path) -> None:
    """TodoApp should have a rename method."""
    app = TodoApp(str(tmp_path / "db.json"))
    todo = app.add("original")

    # Should be able to call rename
    renamed = app.rename(todo.id, "renamed")
    assert renamed.text == "renamed"


def test_app_rename_nonexistent_raises_error(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for non-existent ID."""
    app = TodoApp(str(tmp_path / "db.json"))

    try:
        app.rename(999, "new text")
        raise AssertionError("Expected ValueError for non-existent ID")
    except ValueError as e:
        assert "not found" in str(e).lower()

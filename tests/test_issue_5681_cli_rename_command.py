"""Regression tests for Issue #5681: CLI 'rename' command is missing.

This test file ensures that the CLI has a 'rename' subcommand that allows
users to rename todo items via the command line interface.

Issue #5681: The Todo.rename() method exists in todo.py but there is no
CLI interface to use it.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_has_rename_subcommand(tmp_path, capsys) -> None:
    """CLI should have 'rename' subcommand that changes todo text."""
    db = str(tmp_path / "db.json")
    parser = build_parser()
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    # Now rename it via CLI
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    result = run_command(args)

    assert result == 0, "rename command should succeed"
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "new text" in captured.out


def test_cli_rename_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """CLI rename command should return error for non-existent todo."""
    db = str(tmp_path / "db.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "999", "new text"])
    result = run_command(args)

    assert result == 1, "rename command should fail for non-existent todo"
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_sanitizes_control_characters(tmp_path, capsys) -> None:
    """CLI rename success message should sanitize control characters.

    Issue #5681 acceptance criteria: Success message sanitizes text output
    with _sanitize_text().
    """
    db = str(tmp_path / "db.json")
    parser = build_parser()
    app = TodoApp(db)

    # Add a todo first
    app.add("original")

    # Rename with control characters
    args = parser.parse_args(["--db", db, "rename", "1", "task\n\r\tWith\x00Controls"])
    result = run_command(args)

    assert result == 0, "rename command should succeed"
    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    assert "\\t" in captured.out
    assert "\\x00" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
    assert "\x00" not in captured.out


def test_app_rename_method(tmp_path) -> None:
    """TodoApp should have a rename method that modifies todo text."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original text")
    assert added.id == 1

    renamed = app.rename(1, "renamed text")
    assert renamed.text == "renamed text"

    # Verify persistence
    todos = app.list()
    assert todos[0].text == "renamed text"


def test_app_rename_raises_for_missing_todo(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent todo."""
    app = TodoApp(str(tmp_path / "db.json"))

    try:
        app.rename(999, "new text")
        raise AssertionError("Expected ValueError for non-existent todo")
    except ValueError as e:
        assert "not found" in str(e)

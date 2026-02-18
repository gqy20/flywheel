"""Regression tests for Issue #4245: CLI missing edit command for Todo.rename.

This test file ensures that the CLI supports the 'todo edit <id> <new_text>' command
to modify existing todo text using the Todo.rename method.
"""

from __future__ import annotations

from flywheel.cli import build_parser, main, run_command


def test_cli_edit_command_success(tmp_path) -> None:
    """edit command should successfully rename a todo.

    After adding a todo, the edit command should change its text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo
    args_add = parser.parse_args(["--db", str(db), "add", "Original text"])
    result_add = run_command(args_add)
    assert result_add == 0

    # Edit the todo
    args_edit = parser.parse_args(["--db", str(db), "edit", "1", "Updated text"])
    result_edit = run_command(args_edit)
    assert result_edit == 0

    # Verify the edit by listing
    args_list = parser.parse_args(["--db", str(db), "list"])
    result_list = run_command(args_list)
    assert result_list == 0


def test_cli_edit_command_not_found(tmp_path, capsys) -> None:
    """edit command should return error for non-existent todo id."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_empty_text(tmp_path, capsys) -> None:
    """edit command should return error for empty text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo first
    args_add = parser.parse_args(["--db", str(db), "add", "Some todo"])
    run_command(args_add)

    # Try to edit with empty text
    args = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_whitespace_only_text(tmp_path, capsys) -> None:
    """edit command should return error for whitespace-only text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo first
    args_add = parser.parse_args(["--db", str(db), "add", "Some todo"])
    run_command(args_add)

    # Try to edit with whitespace-only text
    args = parser.parse_args(["--db", str(db), "edit", "1", "   "])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_main_edit_command(tmp_path, capsys) -> None:
    """main() function should handle edit command via CLI."""
    db = tmp_path / "db.json"

    # Add a todo
    result_add = main(["--db", str(db), "add", "First text"])
    assert result_add == 0

    # Edit the todo
    result_edit = main(["--db", str(db), "edit", "1", "Second text"])
    assert result_edit == 0

    captured = capsys.readouterr()
    # Should show the updated text in the output
    assert "Updated" in captured.out or "#1" in captured.out

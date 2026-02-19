"""Regression tests for Issue #4480: Todo.rename() has no CLI command exposure.

This test file ensures that the 'rename' CLI subcommand is available
and properly handles renaming todos.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """'todo rename <id> <text>' command should rename an existing todo."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First, add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0
    capsys.readouterr()  # Clear output

    # Then, rename it
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    result = run_command(args)
    assert result == 0, "rename command should return 0 on success"
    capsys.readouterr()  # Clear output

    # Verify the text was changed
    args = parser.parse_args(["--db", db, "list"])
    run_command(args)
    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "original text" not in captured.out


def test_cli_rename_command_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """rename command should return 1 when todo not found."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename a non-existent todo
    args = parser.parse_args(["--db", db, "rename", "999", "new text"])
    result = run_command(args)

    assert result == 1, "rename command should return 1 on error"
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_outputs_success_message(tmp_path, capsys) -> None:
    """rename command should output a success message with the new text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo
    args = parser.parse_args(["--db", db, "add", "original"])
    run_command(args)
    capsys.readouterr()  # Clear output

    # Rename it
    args = parser.parse_args(["--db", db, "rename", "1", "renamed"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    assert "Renamed" in captured.out
    assert "#1" in captured.out
    assert "renamed" in captured.out

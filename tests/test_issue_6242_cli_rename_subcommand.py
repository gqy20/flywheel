"""Regression tests for Issue #6242: CLI missing 'rename' subcommand.

This test file ensures that the CLI supports a 'rename' subcommand that allows
users to change the text of an existing todo item.

Issue #6242: The Todo.rename() method exists in todo.py but the CLI does not
expose it through a 'rename' subcommand.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_exists() -> None:
    """rename subcommand should be available in the CLI parser."""
    parser = build_parser()
    # Parse the rename command - should not raise an error
    args = parser.parse_args(["rename", "1", "New text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "New text"


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """rename command should successfully change todo text and return exit code 0.

    Acceptance criteria: 'todo rename <id> <text>' command successfully changes
    todo text and returns exit code 0 on success.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"
    capsys.readouterr()  # Clear add output

    # Now rename it
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Updated text"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed with exit code 0"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "Updated text" in captured.out


def test_cli_rename_command_nonexistent_todo(tmp_path, capsys) -> None:
    """rename command should return exit code 1 when todo not found.

    Acceptance criteria: 'todo rename <id> <text>' returns exit code 1 when
    todo not found.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to rename a non-existent todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "New text"])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail with exit code 1 when todo not found"

    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "not found" in captured.err


def test_cli_rename_command_empty_text(tmp_path, capsys) -> None:
    """rename command should return exit code 1 with empty text.

    Acceptance criteria: 'todo rename' with empty text raises error.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail with exit code 1 for empty text"

    captured = capsys.readouterr()
    assert "Error" in captured.err


def test_cli_rename_command_whitespace_only_text(tmp_path, capsys) -> None:
    """rename command should return exit code 1 with whitespace-only text.

    Whitespace-only text should be treated as empty.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with whitespace-only text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "   "])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail with exit code 1 for whitespace-only text"

    captured = capsys.readouterr()
    assert "Error" in captured.err


def test_cli_rename_persists_to_storage(tmp_path, capsys) -> None:
    """rename command should persist changes to storage."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename it
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Updated text"])
    result = run_command(rename_args)
    assert result == 0
    capsys.readouterr()  # Clear rename output

    # List todos to verify the rename persisted
    list_args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(list_args)
    assert result == 0

    captured = capsys.readouterr()
    assert "Updated text" in captured.out
    assert "Original text" not in captured.out

"""Regression tests for Issue #6998: Add CLI 'rename' command to expose Todo.rename() functionality.

This test file ensures that the CLI provides a 'rename' subcommand that allows users
to rename existing todos via the command line.

Acceptance criteria:
- 'todo rename 1 new text' successfully renames todo #1
- 'todo rename 99 x' returns error for non-existent id
- 'todo rename 1 ""' returns error for empty text
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_with_valid_id_and_text(tmp_path, capsys) -> None:
    """rename command should successfully rename an existing todo.

    Issue #6998: 'todo rename 1 new text' should successfully rename todo #1.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"
    capsys.readouterr()  # Clear add output

    # Now rename it
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "New text"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    assert "Renamed #1:" in captured.out
    assert "New text" in captured.out


def test_cli_rename_command_with_invalid_id(tmp_path, capsys) -> None:
    """rename command should return error for non-existent id.

    Issue #6998: 'todo rename 99 x' should return error for non-existent id.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a single todo
    add_args = parser.parse_args(["--db", str(db), "add", "Some task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename non-existent todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "99", "x"])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail for non-existent id"

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "not found" in captured.err


def test_cli_rename_command_with_empty_text(tmp_path, capsys) -> None:
    """rename command should return error for empty text.

    Issue #6998: 'todo rename 1 ""' should return error for empty text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Some task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail for empty text"

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "empty" in captured.err.lower()


def test_cli_rename_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """rename command should sanitize control characters in output.

    Ensures consistency with other CLI commands (add, done, undone) that
    sanitize todo text before output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo with control characters
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename with control characters
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Task\nWith\x1b[31mColor"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\x1b" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\x1b" not in captured.out


def test_cli_rename_preserves_done_status(tmp_path, capsys) -> None:
    """rename command should preserve the done status of the todo.

    Renaming a completed todo should not change its done status.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add and complete a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    done_args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(done_args)
    capsys.readouterr()  # Clear previous output

    # Rename the completed todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Renamed task"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    # List to verify done status is preserved
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "[x]" in captured.out, "Todo should still be marked as done"

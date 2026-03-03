"""Regression tests for Issue #6998: Add CLI 'rename' command to expose Todo.rename() functionality.

This test file ensures that CLI has a 'rename' subcommand that allows users to rename
todos via the command line.

Acceptance criteria:
- 'todo rename 1 new text' successfully renames todo #1
- 'todo rename 99 x' returns error for non-existent id
- 'todo rename 1 ""' returns error for empty text
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_with_valid_id_and_text(tmp_path, capsys) -> None:
    """rename command should successfully rename a todo with valid id and text.

    Issue #6998: 'todo rename 1 new text' should successfully rename todo #1.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"

    # Rename the todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "New text"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "New text" in captured.out


def test_cli_rename_command_with_non_existent_id(tmp_path, capsys) -> None:
    """rename command should return error for non-existent id.

    Issue #6998: 'todo rename 99 x' should return error for non-existent id.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to rename a non-existent todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "99", "new text"])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail for non-existent id"

    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "not found" in captured.err.lower()


def test_cli_rename_command_with_empty_text(tmp_path, capsys) -> None:
    """rename command should return error for empty text.

    Issue #6998: 'todo rename 1 ""' should return error for empty text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail for empty text"

    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "empty" in captured.err.lower()


def test_cli_rename_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """rename command should sanitize control characters in success message.

    Following pattern from Issue #2083: success messages should sanitize
    control characters in todo.text before output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename with control characters
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Task\n\rWith\x00Controls"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    assert "\\x00" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
    assert "\x00" not in captured.out

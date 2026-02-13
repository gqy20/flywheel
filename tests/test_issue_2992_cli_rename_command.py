"""Regression tests for Issue #2992: Add rename command to CLI.

This test file ensures that the CLI exposes a 'rename' subcommand that allows
users to rename todos via the command line interface.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_renames_todo(tmp_path, capsys) -> None:
    """rename command should successfully rename a todo.

    After renaming, the todo text should be updated and output to stdout.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)

    # Clear captured output from add
    capsys.readouterr()

    # Now rename it
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Updated text"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    # Output should confirm the rename
    assert "Updated text" in captured.out
    assert "#1" in captured.out or "1" in captured.out


def test_cli_rename_command_updates_todo_in_storage(tmp_path, capsys) -> None:
    """rename command should persist the new text in storage."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Old text"])
    run_command(add_args)

    # Clear captured output
    capsys.readouterr()

    # Rename it
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Brand new text"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    # Clear captured output
    capsys.readouterr()

    # Verify by listing
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)

    captured = capsys.readouterr()
    assert "Brand new text" in captured.out
    assert "Old text" not in captured.out


def test_cli_rename_command_empty_text_raises_error(tmp_path, capsys) -> None:
    """rename command should error on empty text.

    Empty text should trigger an error message and return non-zero exit code.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Some text"])
    run_command(add_args)

    # Clear captured output
    capsys.readouterr()

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)

    assert result == 1, "rename command should fail on empty text"

    captured = capsys.readouterr()
    # Error message should indicate the issue
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_command_nonexistent_id_raises_error(tmp_path, capsys) -> None:
    """rename command should error on non-existent todo id."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to rename non-existent todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "New text"])
    result = run_command(rename_args)

    assert result == 1, "rename command should fail on non-existent id"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """rename command should sanitize control characters in output."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original"])
    run_command(add_args)

    # Clear captured output
    capsys.readouterr()

    # Rename with control character
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "New\nText"])
    result = run_command(rename_args)

    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    # Output should NOT contain actual newline character
    assert "\n" not in captured.out.strip()

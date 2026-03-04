"""Regression tests for Issue #7121: Todo.rename() method exists but CLI does not expose rename command.

This test file ensures that the CLI exposes a 'rename' command to allow users
to rename existing todos via the command line.

Issue #7121 acceptance criteria:
- Users can rename a todo via CLI: todo rename <id> <new_text>
- Non-existent id returns non-zero exit code and error message
- Empty text is rejected with an error
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_exists_and_works(tmp_path, capsys) -> None:
    """rename command should exist and successfully rename a todo."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    result = run_command(add_args)
    assert result == 0
    capsys.readouterr()  # Clear output

    # Now rename it
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Renamed task"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out

    # Verify the rename persisted by listing
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "Renamed task" in captured.out
    assert "Original task" not in captured.out


def test_cli_rename_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """rename command should return error for non-existent todo id."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to rename a todo that doesn't exist
    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "New text"])
    result = run_command(rename_args)

    assert result == 1, "rename command should return 1 for non-existent id"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_empty_text_rejected(tmp_path, capsys) -> None:
    """rename command should reject empty text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Task to rename"])
    run_command(add_args)
    capsys.readouterr()  # Clear output

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)

    assert result == 1, "rename command should return 1 for empty text"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_whitespace_only_text_rejected(tmp_path, capsys) -> None:
    """rename command should reject whitespace-only text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Task to rename"])
    run_command(add_args)
    capsys.readouterr()  # Clear output

    # Try to rename with whitespace-only text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "   "])
    result = run_command(rename_args)

    assert result == 1, "rename command should return 1 for whitespace-only text"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """rename command should sanitize control characters in output message."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear output

    # Rename with control characters
    rename_args = parser.parse_args(
        ["--db", str(db), "rename", "1", "Task\nWith\x1b[31mColor\x1b[0m"]
    )
    result = run_command(rename_args)
    assert result == 0

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\x1b" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\x1b" not in captured.out

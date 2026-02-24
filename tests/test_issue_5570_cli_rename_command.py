"""Tests for issue #5570: CLI 'rename' command.

Bug: Missing CLI 'rename' command despite Todo.rename() method existing.

Acceptance criteria:
- CLI accepts 'todo rename <id> <new_text>' command
- rename command returns 0 on success
- rename command returns 1 and prints error to stderr if todo not found
- rename command sanitizes output like other commands
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_succeeds(tmp_path, capsys) -> None:
    """CLI rename command should succeed and update todo text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0

    # Now rename it
    args = parser.parse_args(["--db", db, "rename", "1", "renamed task"])
    assert run_command(args) == 0

    # Verify output
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "renamed task" in captured.out


def test_cli_rename_command_returns_error_for_missing_id(tmp_path, capsys) -> None:
    """CLI rename command should return 1 and print error for missing todo."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename a non-existent todo
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_sanitizes_output(tmp_path, capsys) -> None:
    """CLI rename command should sanitize output like other commands."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo with control characters
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0
    capsys.readouterr()  # Clear output

    # Rename with text containing control characters (ANSI escape)
    args = parser.parse_args(["--db", db, "rename", "1", "task\x1b[31mred"])
    assert run_command(args) == 0

    captured = capsys.readouterr()
    # ESC character (0x1b) should be sanitized to escaped representation
    # The raw ESC byte should NOT appear in output, but its escaped form "\\x1b" should
    assert "\x1b" not in captured.out  # Raw ESC byte should not be present
    assert "\\x1b" in captured.out  # Escaped representation should be present

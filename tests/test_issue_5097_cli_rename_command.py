"""Regression tests for Issue #5097: Todo.rename() not exposed via CLI.

This test file ensures that the 'rename' subcommand is available in the CLI
to expose the Todo.rename() functionality to users.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command
import json


def test_cli_rename_command_exists() -> None:
    """The 'rename' subcommand should be available in the CLI parser."""
    parser = build_parser()
    # Parse the rename command - should not raise an error
    args = parser.parse_args(["rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """Calling 'todo rename <id> <new_text>' should update the todo's text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "old text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename the todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "new text"])
    result = run_command(rename_args)

    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out

    # Verify the text was actually updated
    data = json.loads(db.read_text())
    assert data[0]["text"] == "new text"


def test_cli_rename_command_updates_updated_at(tmp_path) -> None:
    """Calling 'todo rename' should update the todo's updated_at timestamp."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original"])
    run_command(add_args)

    # Get original timestamp
    data = json.loads(db.read_text())
    original_updated_at = data[0]["updated_at"]

    # Rename the todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "renamed"])
    run_command(rename_args)

    # Verify updated_at changed
    data = json.loads(db.read_text())
    assert data[0]["updated_at"] != original_updated_at


def test_cli_rename_command_nonexistent_id(tmp_path, capsys) -> None:
    """Renaming a non-existent todo should raise 'Todo #X not found'."""
    db = tmp_path / "db.json"
    parser = build_parser()

    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "new text"])
    result = run_command(rename_args)

    assert result == 1, "rename command should fail for non-existent todo"

    captured = capsys.readouterr()
    assert "Todo #999 not found" in captured.err


def test_cli_rename_command_empty_text(tmp_path, capsys) -> None:
    """Renaming with empty text should raise ValueError."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original"])
    run_command(add_args)

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)

    assert result == 1, "rename command should fail for empty text"

    captured = capsys.readouterr()
    assert "cannot be empty" in captured.err.lower()


def test_cli_rename_command_whitespace_only_text(tmp_path, capsys) -> None:
    """Renaming with whitespace-only text should raise ValueError."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original"])
    run_command(add_args)

    # Try to rename with whitespace-only text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "   "])
    result = run_command(rename_args)

    assert result == 1, "rename command should fail for whitespace-only text"

    captured = capsys.readouterr()
    assert "cannot be empty" in captured.err.lower()


def test_cli_rename_command_sanitizes_output(tmp_path, capsys) -> None:
    """rename command should sanitize control characters in success message."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename with control characters
    rename_args = parser.parse_args(
        ["--db", str(db), "rename", "1", "new\n\r\ttext"]
    )
    result = run_command(rename_args)

    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    # Control characters should be escaped, not rendered
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    assert "\\t" in captured.out
    # No actual control characters in output
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out

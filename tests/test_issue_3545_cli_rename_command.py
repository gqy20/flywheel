"""Tests for CLI rename command - Issue #3545."""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """Running 'todo rename 1 new text' successfully renames todo #1."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "new text" in captured.out

    # Verify the rename persisted
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "original text" not in captured.out


def test_cli_rename_command_nonexistent_id(tmp_path, capsys) -> None:
    """Running 'todo rename 99 text' with non-existent ID returns error code 1."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first so we have id 1, but try to rename id 99
    args = parser.parse_args(["--db", db, "add", "some task"])
    assert run_command(args) == 0

    # Try to rename non-existent todo
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_empty_text(tmp_path, capsys) -> None:
    """Running 'todo rename 1 \"\"' with empty text returns error code 1."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()

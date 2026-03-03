"""Tests for issue #6926: CLI does not expose rename functionality."""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_subcommand_exists(tmp_path, capsys) -> None:
    """Issue #6926: 'rename' subcommand should be available in CLI."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Rename the todo via CLI
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "Renamed #1" in captured.out


def test_cli_rename_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """Issue #6926: CLI rename should return exit code 1 when todo not found."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Attempt rename of non-existent ID
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_persists_change(tmp_path, capsys) -> None:
    """Issue #6926: Rename via CLI should persist the change."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add and rename
    args = parser.parse_args(["--db", db, "add", "old text"])
    assert run_command(args) == 0
    capsys.readouterr()  # Clear output

    args = parser.parse_args(["--db", db, "rename", "1", "updated text"])
    assert run_command(args) == 0
    capsys.readouterr()  # Clear output

    # Verify the change persisted
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "updated text" in captured.out
    assert "old text" not in captured.out

"""Regression tests for Issue #2532: CLI 'add' command lacks test coverage for whitespace-only input validation.

This test file ensures that CLI 'add' command properly rejects whitespace-only input
via exit code 1 and appropriate error message to stderr.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_add_command_rejects_single_space(tmp_path, capsys) -> None:
    """add command should reject single space as input.

    When adding a todo with only whitespace, the CLI should return exit code 1
    and output an error message indicating the text cannot be empty.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", " "])

    result = run_command(args)
    assert result == 1, "add command should return 1 for whitespace-only input"

    captured = capsys.readouterr()
    # Error message should be in stderr, not stdout
    assert "Error:" in captured.err
    assert "Todo text cannot be empty" in captured.err


def test_cli_add_command_rejects_multiple_spaces(tmp_path, capsys) -> None:
    """add command should reject multiple spaces as input."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "   "])

    result = run_command(args)
    assert result == 1, "add command should return 1 for whitespace-only input"

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "Todo text cannot be empty" in captured.err


def test_cli_add_command_rejects_tabs(tmp_path, capsys) -> None:
    """add command should reject tabs as input."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "\t"])

    result = run_command(args)
    assert result == 1, "add command should return 1 for whitespace-only input"

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "Todo text cannot be empty" in captured.err


def test_cli_add_command_rejects_newlines(tmp_path, capsys) -> None:
    """add command should reject newlines as input."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "\n"])

    result = run_command(args)
    assert result == 1, "add command should return 1 for whitespace-only input"

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "Todo text cannot be empty" in captured.err


def test_cli_add_command_rejects_mixed_whitespace(tmp_path, capsys) -> None:
    """add command should reject mixed whitespace (spaces, tabs, newlines) as input."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "  \t\n  "])

    result = run_command(args)
    assert result == 1, "add command should return 1 for whitespace-only input"

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "Todo text cannot be empty" in captured.err


def test_cli_add_command_trims_whitespace_from_valid_input(tmp_path, capsys) -> None:
    """add command should trim leading/trailing whitespace from valid input."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "  Buy milk  "])

    result = run_command(args)
    assert result == 0, "add command should succeed for input with trimmed whitespace"

    captured = capsys.readouterr()
    # Output should contain the trimmed text
    assert "Buy milk" in captured.out
    # Should not have extra spaces
    assert "  Buy milk  " not in captured.out

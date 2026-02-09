"""Regression test for Issue #2532: CLI 'add' command lacks test coverage for whitespace-only input validation.

This test file ensures that the CLI 'add' command properly validates and rejects
whitespace-only input, returning an appropriate error code and message.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_add_command_rejects_whitespace_only(tmp_path, capsys) -> None:
    """add command should reject whitespace-only input with exit code 1.

    When adding a todo with only whitespace characters, the CLI should return
    exit code 1 and output an appropriate error message to stderr.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "   "])

    result = run_command(args)
    assert result == 1, "add command should return exit code 1 for whitespace-only input"

    captured = capsys.readouterr()
    # Error message should contain information about empty text
    assert "empty" in captured.err.lower(), f"Expected error message about empty text, got: {captured.err}"


def test_cli_add_command_rejects_tab_only(tmp_path, capsys) -> None:
    """add command should reject tab-only input with exit code 1."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "\t"])

    result = run_command(args)
    assert result == 1, "add command should return exit code 1 for tab-only input"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower(), f"Expected error message about empty text, got: {captured.err}"


def test_cli_add_command_rejects_newline_only(tmp_path, capsys) -> None:
    """add command should reject newline-only input with exit code 1."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "\n"])

    result = run_command(args)
    assert result == 1, "add command should return exit code 1 for newline-only input"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower(), f"Expected error message about empty text, got: {captured.err}"


def test_cli_add_command_rejects_mixed_whitespace(tmp_path, capsys) -> None:
    """add command should reject mixed whitespace input with exit code 1."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "  \t\n  "])

    result = run_command(args)
    assert result == 1, "add command should return exit code 1 for mixed whitespace input"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower(), f"Expected error message about empty text, got: {captured.err}"

"""Regression tests for Issue #2532: CLI add command lacks whitespace-only input validation.

This test file ensures that the CLI add command properly validates and rejects
whitespace-only input, returning the correct exit code and error message.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_add_command_rejects_whitespace_only(tmp_path, capsys) -> None:
    """CLI add command should reject whitespace-only input with exit code 1.

    When the add command is given only whitespace as the todo text, it should:
    1. Return exit code 1
    2. Output an error message to stderr containing "cannot be empty"
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "   "])

    result = run_command(args)

    assert result == 1, "add command should fail with whitespace-only input"

    captured = capsys.readouterr()
    assert "cannot be empty" in captured.err.lower(), (
        f"Expected error message about empty text, got: {captured.err}"
    )


def test_cli_add_command_rejects_tab_whitespace(tmp_path, capsys) -> None:
    """CLI add command should reject tab-only input with exit code 1."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "\t\n"])

    result = run_command(args)

    assert result == 1, "add command should fail with tab-only input"

    captured = capsys.readouterr()
    assert "cannot be empty" in captured.err.lower(), (
        f"Expected error message about empty text, got: {captured.err}"
    )

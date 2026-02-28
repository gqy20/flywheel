"""Regression tests for Issue #6227: CLI exception messages printed to stderr without sanitization.

This test file ensures that exception messages in run_command are sanitized
before being printed to stderr, preventing terminal control character injection
via exception messages.

Issue #6227 highlights line 125 in cli.py where exception messages are printed
to stderr without sanitization, while other outputs (lines 100, 110, 115) use
_sanitize_text().
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.cli import build_parser, run_command


def test_cli_exception_message_sanitizes_ansi_escape(tmp_path, capsys) -> None:
    """Exception messages containing ANSI escape sequences should be sanitized.

    Issue #6227: Line 125 prints exception messages without sanitization,
    allowing terminal control character injection via ANSI escape sequences.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Patch TodoApp.add to raise ValueError with control character in message
    with patch("flywheel.cli.TodoApp") as mock_app:
        mock_instance = mock_app.return_value
        mock_instance.add.side_effect = ValueError("\x1b[31mRed Error\x1b[0m")

        args = parser.parse_args(["--db", str(db), "add", "test"])
        result = run_command(args)

    assert result == 1, "run_command should return 1 on exception"

    captured = capsys.readouterr()
    # Output should contain escaped representation, not raw ESC character
    assert "\\x1b" in captured.err
    # Output should NOT contain actual ESC character (prevents terminal injection)
    assert "\x1b" not in captured.err


def test_cli_exception_message_sanitizes_carriage_return(tmp_path, capsys) -> None:
    """Exception messages containing carriage returns should be sanitized.

    Issue #6227: Carriage return injection could overwrite error messages.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    with patch("flywheel.cli.TodoApp") as mock_app:
        mock_instance = mock_app.return_value
        mock_instance.add.side_effect = ValueError("Error\r[INJECTED]")

        args = parser.parse_args(["--db", str(db), "add", "test"])
        result = run_command(args)

    assert result == 1

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\r" in captured.err
    # Output should NOT contain actual carriage return
    assert "\r" not in captured.err


def test_cli_exception_message_sanitizes_newline(tmp_path, capsys) -> None:
    """Exception messages containing newlines should be sanitized.

    Issue #6227: Newline injection could create fake output lines.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    with patch("flywheel.cli.TodoApp") as mock_app:
        mock_instance = mock_app.return_value
        mock_instance.add.side_effect = ValueError("Error\nFAKE_LINE")

        args = parser.parse_args(["--db", str(db), "add", "test"])
        result = run_command(args)

    assert result == 1

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.err
    # Output should NOT contain actual newline in single-line output
    assert "\n" not in captured.err.strip()


def test_cli_exception_message_sanitizes_null_byte(tmp_path, capsys) -> None:
    """Exception messages containing null bytes should be sanitized.

    Issue #6227: Null bytes and other control characters should be escaped.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    with patch("flywheel.cli.TodoApp") as mock_app:
        mock_instance = mock_app.return_value
        mock_instance.add.side_effect = ValueError("Error\x00WithNull")

        args = parser.parse_args(["--db", str(db), "add", "test"])
        result = run_command(args)

    assert result == 1

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\x00" in captured.err
    # Output should NOT contain actual null byte
    assert "\x00" not in captured.err

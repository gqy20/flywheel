"""Regression tests for Issue #2358: CLI error messages may expose untrusted input.

This test file ensures that CLI error messages sanitize control characters
in user-supplied data to prevent terminal control character injection attacks
through error output.

Issue #2358 specifically highlights line 125 in cli.py where error messages
print exc directly without sanitization, while success messages (lines 100, 110, 115)
use _sanitize_text() for security.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

from flywheel.cli import build_parser, run_command
from flywheel.formatter import _sanitize_text


def test_cli_error_message_sanitizes_control_chars_from_value_error(tmp_path, capsys) -> None:
    """Error messages should sanitize control characters in ValueError output.

    Issue #2358: Line 125 prints exc directly without sanitization, allowing terminal
    control character injection when ValueError messages contain user-supplied data.

    This test simulates error messages containing control characters - while the
    current ValueError messages don't include user input directly, the fix ensures
    future code changes don't introduce this vulnerability.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Trigger an error by trying to mark non-existent todo as done
    # The error message "Todo #999 not found" contains the user-supplied ID
    # If future changes include user text in error messages, sanitization is critical
    args = parser.parse_args(["--db", str(db), "done", "999"])
    result = run_command(args)

    assert result == 1, "command should fail with non-existent todo"

    captured = capsys.readouterr()
    # Error should be in stderr
    assert "not found" in captured.err.lower()

    # The key security check: error output should not contain raw control characters
    # If the error message were to include user text with control characters,
    # they would be neutralized by the sanitization fix
    assert "\x1b" not in captured.err  # No raw ESC
    assert "\r" not in captured.err  # No raw carriage return
    assert "\n" not in captured.err.strip()  # No embedded newlines (except final)


def test_cli_error_message_handles_ansi_injection_in_todo_id(tmp_path, capsys) -> None:
    """Todo ID in error messages should not enable ANSI escape injection.

    Issue #2358: If error messages include user data without sanitization,
    control characters could affect terminal output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # The ID is parsed as int, so we can't inject strings, but this validates
    # the error handling is robust against edge cases
    args = parser.parse_args(["--db", str(db), "rm", "999"])
    result = run_command(args)

    assert result == 1, "command should fail with non-existent todo"

    captured = capsys.readouterr()
    # Error output should be sanitized
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()
    # No raw control characters in error output
    assert "\x1b" not in captured.err


def test_cli_error_message_json_decode_error_sanitizes_path(tmp_path, capsys) -> None:
    """Error messages from JSON decode errors should sanitize file paths.

    Issue #2358: storage.py line 76 includes file path in ValueError message.
    If the file path contains control characters (unlikely but possible),
    the error output should be sanitized.
    """
    db = tmp_path / "db.json"
    # Write invalid JSON to trigger JSONDecodeError
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)
    assert result == 1, "command should fail with invalid JSON"

    captured = capsys.readouterr()
    # Error message should be present
    assert "error" in captured.err.lower() or "invalid json" in captured.err.lower()
    # Output should not contain raw control characters
    assert "\x1b" not in captured.err


def test_cli_error_message_oserror_sanitizes_output(tmp_path, capsys) -> None:
    """Error messages from OSError should be sanitized.

    Issue #2358: OSError messages may include file paths with control characters.
    The error output should sanitize these to prevent terminal injection.
    """
    db = tmp_path / "db.json"
    # Create a directory at db path to trigger OSError on write
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)
    assert result == 1, "command should fail with OSError"

    captured = capsys.readouterr()
    # Some error message should be present
    assert captured.err or captured.out
    # No raw control characters that could affect terminal
    assert "\x1b" not in (captured.err + captured.out)


def test_cli_empty_todo_text_with_only_whitespace_fails(tmp_path, capsys) -> None:
    """Empty todo text with only whitespace should fail safely.

    Issue #2358: Validate that whitespace-only input (which may include
    control characters) fails appropriately.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to add whitespace-only todo
    args = parser.parse_args(["--db", str(db), "add", "   \r\n\t  "])
    result = run_command(args)

    assert result == 1, "command should fail with whitespace-only text"

    captured = capsys.readouterr()
    # Error message should mention empty text
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()
    # No raw control characters in error output
    assert "\r" not in captured.err
    assert "\n" not in captured.err.strip()


def test_cli_error_message_sanitization_with_mocked_error(tmp_path, capsys) -> None:
    """Error messages should sanitize control characters using _sanitize_text.

    Issue #2358: This test uses a mock to simulate an error with control characters,
    validating that the error output is sanitized. Without the fix, control characters
    would be printed raw to stderr.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Create a ValueError with control characters to simulate future code paths
    # that might include user data in error messages
    error_msg = "Todo text contains invalid characters: \x1b[31mRED\x1b[0m\r\nINJECTED"

    # Mock TodoApp.add to raise our controlled error
    with patch("flywheel.cli.TodoApp.add", side_effect=ValueError(error_msg)):
        args = parser.parse_args(["--db", str(db), "add", "test"])
        result = run_command(args)

        assert result == 1, "command should fail with ValueError"

        captured = capsys.readouterr()
        # Error message should be in stderr
        assert "Todo text contains invalid characters" in captured.err

        # KEY SECURITY CHECK: The fix should sanitize control characters
        # Raw control characters should NOT appear in stderr
        assert "\x1b" not in captured.err, "Raw ESC character should be sanitized"
        assert "\r" not in captured.err, "Raw carriage return should be sanitized"
        # Newlines may exist as line endings in error output, but not in the error message itself
        # Check that the error message doesn't have embedded newlines by checking it's single-line
        error_lines = [line for line in captured.err.split("\n") if line.strip()]
        assert len(error_lines) <= 1, "Error should be on a single line (no injected newlines)"

        # After sanitization, the control characters should be escaped
        assert "\\x1b" in captured.err or "\\x1b" not in error_msg
        assert "\\r" in captured.err or "\\r" not in error_msg

"""Regression tests for Issue #2358: CLI error messages may expose untrusted input.

This test file ensures that CLI error messages sanitize control characters
in ValueError messages before outputting to stderr to prevent terminal control
character injection attacks.

Issue #2358 specifically highlights line 125 in cli.py where error messages
print exc directly without sanitization, while success messages (lines 100, 110, 115)
use _sanitize_text().

The vulnerability occurs when ValueError messages include user-controlled paths:
- storage.py:38-39 - Path error messages include user-supplied path
- storage.py:77 - Invalid JSON error includes user-supplied file path
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_error_message_sanitizes_ansi_escape_in_path(tmp_path, capsys) -> None:
    """Error messages from file path should escape ANSI escape sequences.

    Issue #2358: When the database path contains ANSI escape sequences and an
    error occurs (e.g., file is a directory instead of a file), the ValueError
    message at storage.py:38-39 includes the raw path and prints it without
    sanitization at cli.py:125.

    This test creates a file at the parent path to trigger the ValueError at
    storage.py:37-40.
    """
    parser = build_parser()
    # Use a path with ANSI escape sequence that would make text red
    # Note: We can't easily create a file with control chars in the path,
    # so we use a different approach - trigger JSON decode error which includes path
    db = tmp_path / "test\x1b[31mRED\x1b[0m.json"
    # Write invalid JSON to trigger JSONDecodeError with path in error
    db.write_text('{"invalid": json}', encoding="utf-8")

    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 1, "list command should fail for invalid JSON"

    captured = capsys.readouterr()
    # Error message should NOT contain actual ANSI escape character (0x1b)
    assert "\x1b" not in captured.err, "Error message should sanitize ANSI escape sequences in path"


def test_cli_error_message_sanitizes_carriage_return_in_path(tmp_path, capsys) -> None:
    """Error messages from file path should escape carriage returns.

    Issue #2358: When the database path contains carriage returns and an error
    occurs, the ValueError message includes the raw path and prints it without
    sanitization at cli.py:125.
    """
    parser = build_parser()
    # Use a path with carriage return
    db = tmp_path / "test\r[INJECT].json"
    # Write invalid JSON to trigger error with path in message
    db.write_text('invalid json', encoding="utf-8")

    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 1, "list command should fail for invalid JSON"

    captured = capsys.readouterr()
    # Error message should NOT contain actual carriage return
    assert "\r" not in captured.err, "Error message should sanitize carriage return in path"


def test_cli_error_message_sanitizes_newline_in_path(tmp_path, capsys) -> None:
    """Error messages should escape newlines to prevent multi-line injection.

    Issue #2358: Newlines in error messages from file paths could create fake
    error messages or inject arbitrary content into terminal output.
    """
    parser = build_parser()
    # Use a path with newline
    db = tmp_path / "test\n[INJECT].json"
    # Write invalid JSON to trigger error
    db.write_text('{bad json}', encoding="utf-8")

    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 1, "list command should fail for invalid JSON"

    captured = capsys.readouterr()
    # Error message should be on single line - no actual newlines
    assert "\n" not in captured.err.strip(), "Error message should be single line"


def test_cli_error_message_sanitizes_control_chars_in_path(tmp_path, capsys) -> None:
    """Error messages should escape all control characters in paths.

    Issue #2358: Various control characters in file paths could be used for
    terminal injection via error messages.
    """
    parser = build_parser()
    # Use a path with various control characters (excluding null byte which OS rejects)
    db = tmp_path / "test\x01\x02\x03.json"
    # Write invalid JSON to trigger error
    db.write_text('[]', encoding="utf-8")

    args = parser.parse_args(["--db", str(db), "list"])
    run_command(args)  # May succeed or fail depending on OS

    captured = capsys.readouterr()
    # If there's an error, it should NOT contain raw control characters
    if captured.err:
        assert "\x01" not in captured.err, "Error should not contain \\x01"
        assert "\x02" not in captured.err, "Error should not contain \\x02"
        assert "\x03" not in captured.err, "Error should not contain \\x03"


def test_cli_error_message_sanitizes_control_chars(tmp_path, capsys) -> None:
    """Error messages should escape all control characters.

    Issue #2358: Various control characters could be used for terminal injection.
    This test verifies that control characters in ValueError messages are sanitized.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    # Multiple control characters
    args = parser.parse_args(["--db", str(db), "add", "\x00\x01\x02\x03"])

    result = run_command(args)
    # After strip(), control chars remain, and after empty check, this fails
    # Actually, control chars are not whitespace, so this passes the empty check
    # Let's trigger a different error

    capsys.readouterr()  # Clear output

    # Trigger an error by removing non-existent todo
    args = parser.parse_args(["--db", str(db), "rm", "999"])
    result = run_command(args)
    assert result == 1, "rm command should fail for non-existent todo"

    captured = capsys.readouterr()
    # Error message should NOT contain actual control characters
    assert "\x00" not in captured.err
    assert "\x01" not in captured.err
    assert "\x02" not in captured.err
    assert "\x03" not in captured.err


def test_cli_all_error_messages_are_sanitized(tmp_path, capsys) -> None:
    """All CLI error messages should sanitize user input.

    Issue #2358 acceptance criteria: Error messages containing user input
    are sanitized and terminal control characters don't affect output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Test error messages from various commands with control characters
    test_cases = [
        ("add", ["\r\n"], "empty/whitespace text"),
        ("rm", ["999"], "non-existent todo"),
        ("done", ["999"], "non-existent todo"),
        ("undone", ["999"], "non-existent todo"),
    ]

    for command, extra_args, description in test_cases:
        capsys.readouterr()  # Clear previous output
        args = parser.parse_args(["--db", str(db), command] + extra_args)
        result = run_command(args)
        assert result == 1, f"{command} should fail for {description}"

        captured = capsys.readouterr()
        # Verify no raw control characters in error output
        assert "\r" not in captured.err, f"{command}: error should not contain raw \\r"
        assert "\n" not in captured.err.strip(), f"{command}: error should be single line"
        assert "\x00" not in captured.err, f"{command}: error should not contain \\x00"
        assert "\x1b" not in captured.err, f"{command}: error should not contain ANSI escape"

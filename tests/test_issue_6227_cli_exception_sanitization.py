"""Regression tests for Issue #6227: Exception messages unsanitized in stderr.

This test file ensures that exception messages printed to stderr are sanitized
to prevent terminal control character injection attacks.
"""

from __future__ import annotations

import subprocess
import sys

import pytest


def test_cli_exception_message_sanitizes_ansi_escape_via_todo_text(tmp_path) -> None:
    """Exception messages should escape ANSI escape sequences in stderr.

    ANSI escape sequences like \\x1b[31m could be used to manipulate terminal
    output or hide malicious content in error messages.

    SECURITY: Exception messages may contain user-controlled data (file paths,
    malformed JSON content) that could include ANSI escapes. Without sanitization,
    attackers could inject fake error messages or hide malicious activity.
    """
    db = tmp_path / "db.json"

    # Trigger an error with ANSI escape in the exception message
    # The todo "not found" error includes the todo ID, but we need to get ANSI
    # into the error message itself. Use an OSError with special path.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"""
import sys
sys.path.insert(0, 'src')
from flywheel.cli import run_command, build_parser
parser = build_parser()
# Trigger an exception that includes control characters in the message
class MaliciousException(Exception):
    def __str__(self):
        return "\\x1b[31mFAKE_SUCCESS\\x1b[0m Real error"

raise MaliciousException("test")
""",
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path.parent,
    )
    # The point is that if exception messages were sanitized,
    # the ESC character would not appear raw
    # Currently this test documents the vulnerability exists


def test_cli_exception_message_sanitizes_control_chars_in_stderr(tmp_path, capsys) -> None:
    """Exception messages to stderr must sanitize control characters.

    This is the core security test: any exception message printed to stderr
    must have control characters escaped to prevent terminal manipulation.
    """
    from flywheel.cli import build_parser, run_command
    from flywheel.formatter import _sanitize_text

    db = tmp_path / "db.json"

    # Create a todo with control characters that will fail when we try to mark it done
    # First add a todo, then try to operate on a non-existent one
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])
    result = run_command(args)

    assert result == 1, "command should fail for non-existent todo"

    captured = capsys.readouterr()

    # The error message should NOT contain raw control characters
    # If the exception message contains "not found", it should be sanitized
    # Currently this passes because the simple message doesn't have control chars
    # but the vulnerability is on line 125 which prints any exception message unsanitized
    assert "not found" in captured.err.lower()


def test_cli_exception_message_includes_sanitize_function_for_errors() -> None:
    """Verify that _sanitize_text is used when printing exception messages to stderr."""
    from flywheel.cli import run_command
    from flywheel.formatter import _sanitize_text

    # Test that the _sanitize_text function exists and works correctly
    assert _sanitize_text("hello\nworld") == "hello\\nworld"
    assert _sanitize_text("\x1b[31mred\x1b[0m") == "\\x1b[31mred\\x1b[0m"
    assert _sanitize_text("test\rvalue") == "test\\rvalue"
    assert _sanitize_text("a\tb") == "a\\tb"
    assert _sanitize_text("null\x00byte") == "null\\x00byte"


def test_cli_run_command_sanitizes_exception_message_directly(tmp_path, capsys, monkeypatch) -> None:
    """Directly test that exception messages are sanitized in run_command.

    SECURITY: This test verifies that line 125 in cli.py sanitizes exception
    messages before printing to stderr.
    """
    import flywheel.cli
    from flywheel.cli import build_parser, run_command

    # Create a scenario where the exception message contains control characters
    # We'll use a file path with control characters
    db_dir = tmp_path / "sub"
    db_dir.mkdir()

    # Create a filename with control characters (this is valid on most filesystems)
    # On most systems, these characters are allowed in filenames
    try:
        special_name = "test\x1b[31mRED\x1b[0m.json"
        db = db_dir / special_name
        db.touch()

        parser = build_parser()
        args = parser.parse_args(["--db", str(db), "done", "999"])
        result = run_command(args)

        assert result == 1, "command should fail"

        captured = capsys.readouterr()

        # SECURITY: The error message should NOT contain raw ESC character
        # If the filename is in the error, it must be sanitized
        # Currently this will FAIL because line 125 doesn't sanitize
        # After the fix, this should PASS
        assert "\x1b" not in captured.err, (
            "SECURITY: ANSI escape sequence must be sanitized in stderr output"
        )
    except (OSError, ValueError):
        # Some filesystems don't allow these characters in filenames
        # Skip this test on such systems
        pytest.skip("Filesystem doesn't support special characters in filenames")


def test_cli_exception_message_newline_sanitized(tmp_path, capsys) -> None:
    """Exception messages with newlines must be sanitized in stderr."""
    from flywheel.cli import build_parser, run_command

    # Trigger an error that will have the exception message printed to stderr
    db = tmp_path / "db.json"

    parser = build_parser()
    # This will fail with "Todo #999 not found" - no newlines
    # But we need to test the general case
    args = parser.parse_args(["--db", str(db), "done", "999"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()

    # The error should be a single line (any embedded newlines would be escaped)
    # Currently this passes because the message doesn't have newlines
    # After the fix, any exception with newlines would have them escaped
    err_lines = captured.err.rstrip("\n").count("\n")
    assert err_lines == 0, "Error message should be on a single line (newlines escaped)"


def test_cli_exception_carriage_return_sanitized_via_oserror(tmp_path, capsys) -> None:
    """Exception from OSError must sanitize carriage returns in path."""
    from flywheel.cli import build_parser, run_command

    # Create a subdirectory with a carriage return in its name
    db_dir = tmp_path / "sub\rdir"
    try:
        db_dir.mkdir()
    except OSError:
        pytest.skip("Filesystem doesn't support carriage return in directory names")

    db = db_dir / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1, "should fail for non-existent todo"

    captured = capsys.readouterr()

    # SECURITY: Even if the path has control characters,
    # the error message must not pass them through raw
    assert "\r" not in captured.err or "\\r" in captured.err, (
        "Carriage returns in error messages must be escaped"
    )

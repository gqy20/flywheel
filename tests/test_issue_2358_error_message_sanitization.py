"""Regression tests for Issue #2358: Error messages expose untrusted control characters.

This test file ensures that CLI error messages sanitize control characters
before outputting to stderr to prevent terminal control character injection
attacks. Success messages already use _sanitize_text() but error messages
did not, creating an inconsistency that could be exploited.

The vulnerability is that when ValueError exceptions contain user-supplied
input (like todo text or file paths with control characters), the exception
handler prints them directly to stderr without sanitization.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.cli import build_parser, run_command
from flywheel.formatter import _sanitize_text


def test_cli_valueerror_with_control_chars_is_sanitized(tmp_path, capsys) -> None:
    """ValueError messages containing control characters should be sanitized.

    This test directly simulates the vulnerability: if a ValueError is raised
    with control characters in its message, the error output to stderr should
    have those characters escaped.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Mock TodoApp.add to raise ValueError with control characters
    # This simulates a scenario where user input leaks into error messages
    with patch("flywheel.cli.TodoApp.add") as mock_add:
        # Simulate ValueError with user-supplied control characters
        mock_add.side_effect = ValueError("Todo \x1b[31mRED\x1b[0m not found")

        args = parser.parse_args(["--db", str(db), "add", "test"])
        result = run_command(args)

    assert result == 1, "should return 1 on ValueError"

    captured = capsys.readouterr()
    # Error message should be in stderr
    assert "error" in captured.err.lower()
    # Error message should NOT contain raw ANSI escape character
    # The fix should escape it to \\x1b
    assert "\x1b" not in captured.err


def test_cli_valueerror_with_newline_is_sanitized(tmp_path, capsys) -> None:
    """ValueError messages containing newlines should be sanitized.

    Newlines in error messages could split the output and potentially
    inject fake todos or manipulate terminal display.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Mock TodoApp.list to raise ValueError with newline
    with patch("flywheel.cli.TodoApp.list") as mock_list:
        # Simulate ValueError with control character
        mock_list.side_effect = ValueError("Error:\nTodo #1 not found")

        args = parser.parse_args(["--db", str(db), "list"])
        result = run_command(args)

    assert result == 1, "should return 1 on ValueError"

    captured = capsys.readouterr()
    # Error message should be in stderr
    assert captured.err
    # Error message should NOT contain actual newline (should be escaped)
    # The fix should convert \n to \\n
    assert "\n" not in captured.err.strip()


def test_cli_valueerror_with_carriage_return_is_sanitized(tmp_path, capsys) -> None:
    """ValueError messages containing carriage returns should be sanitized.

    Carriage returns in error messages could overwrite terminal output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Mock TodoApp.remove to raise ValueError with carriage return
    with patch("flywheel.cli.TodoApp.remove") as mock_remove:
        # Simulate ValueError with control character
        mock_remove.side_effect = ValueError("Error:\rTodo #999 removed")

        args = parser.parse_args(["--db", str(db), "rm", "999"])
        result = run_command(args)

    assert result == 1, "should return 1 on ValueError"

    captured = capsys.readouterr()
    # Error message should be in stderr
    assert captured.err
    # Error message should NOT contain raw carriage return
    # The fix should convert \r to \\r
    assert "\r" not in captured.err


def test_cli_valueerror_with_tab_is_sanitized(tmp_path, capsys) -> None:
    """ValueError messages containing tabs should be sanitized.

    Tabs in error messages could misalign output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Mock TodoApp.add to raise ValueError with tab
    with patch("flywheel.cli.TodoApp.add") as mock_add:
        # Simulate ValueError with control character
        mock_add.side_effect = ValueError("Error:\t\tInvalid todo text")

        args = parser.parse_args(["--db", str(db), "add", "test"])
        result = run_command(args)

    assert result == 1, "should return 1 on ValueError"

    captured = capsys.readouterr()
    # Error message should be in stderr
    assert captured.err
    # Error message should NOT contain raw tab character
    # The fix should convert \t to \\t
    assert "\t" not in captured.err


def test_cli_valueerror_with_null_byte_is_sanitized(tmp_path, capsys) -> None:
    """ValueError messages containing null bytes should be sanitized.

    Null bytes in error messages could truncate output in some terminals.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Mock TodoApp.add to raise ValueError with null byte
    with patch("flywheel.cli.TodoApp.add") as mock_add:
        # Simulate ValueError with control character
        mock_add.side_effect = ValueError("Error\x00: Invalid input")

        args = parser.parse_args(["--db", str(db), "add", "test"])
        result = run_command(args)

    assert result == 1, "should return 1 on ValueError"

    captured = capsys.readouterr()
    # Error message should be in stderr
    assert captured.err
    # Error message should NOT contain raw null byte
    # The fix should convert \x00 to \\x00
    assert "\x00" not in captured.err


def test_cli_success_messages_remain_sanitized(tmp_path, capsys) -> None:
    """Existing success message sanitization should remain intact.

    This ensures the fix for error messages doesn't break the existing
    sanitization of success messages (which already use _sanitize_text()).
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo with control characters
    args = parser.parse_args(["--db", str(db), "add", "Buy milk\nFAKE"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Success message should contain escaped newline
    assert "\\n" in captured.out
    # Should not contain actual newline (single line output)
    assert "\n" not in captured.out.strip()


def test_sanitize_text_escapes_all_control_characters() -> None:
    """Verify _sanitize_text properly escapes all control characters.

    This documents the expected behavior for error message sanitization.
    """
    # Test newline
    assert _sanitize_text("line1\nline2") == "line1\\nline2"
    # Test carriage return
    assert _sanitize_text("text\rmore") == "text\\rmore"
    # Test tab
    assert _sanitize_text("a\tb") == "a\\tb"
    # Test ANSI escape
    assert _sanitize_text("\x1b[31mRED\x1b[0m") == "\\x1b[31mRED\\x1b[0m"
    # Test null byte
    assert _sanitize_text("before\x00after") == "before\\x00after"

"""Regression tests for Issue #6227: CLI exception message sanitization.

This test file ensures that exception messages printed to stderr are
sanitized to prevent terminal control character injection attacks.

Issue #6227 specifically highlights line 125 in cli.py where exception
messages are printed to stderr without sanitization.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_exception_message_sanitizes_ansi_escape(tmp_path, capsys) -> None:
    """Exception messages containing ANSI escape sequences should be sanitized.

    Issue #6227: Line 125 prints exception message to stderr without sanitization,
    allowing terminal control character injection via ANSI escape sequences.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Trigger an error with control character in message
    # Marking a non-existent todo will raise ValueError with the id in the message
    args = parser.parse_args(["--db", str(db), "done", "999"])

    # First, let's test with a more direct approach - we'll monkey-patch to inject
    # control characters into the exception message
    import flywheel.cli as cli_module

    original_mark_done = cli_module.TodoApp.mark_done

    def patched_mark_done(self, todo_id):
        # Raise ValueError with control characters in message
        raise ValueError(f"Todo \x1b[31m#999\x1b[0m not found")

    cli_module.TodoApp.mark_done = patched_mark_done

    try:
        result = run_command(args)
        assert result == 1, "run_command should return 1 on error"

        captured = capsys.readouterr()
        # Error message should be in stderr
        assert captured.err, "Error message should be in stderr"

        # Output should contain escaped representation
        assert "\\x1b" in captured.err, "ANSI escape should be escaped in stderr"
        # Output should NOT contain actual ESC character
        assert "\x1b" not in captured.err, "Actual ESC character should not appear in stderr"
    finally:
        cli_module.TodoApp.mark_done = original_mark_done


def test_cli_exception_message_sanitizes_newline(tmp_path, capsys) -> None:
    """Exception messages containing newlines should be sanitized.

    Issue #6227: Newline injection could create fake error messages in output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    args = parser.parse_args(["--db", str(db), "done", "999"])

    import flywheel.cli as cli_module

    original_mark_done = cli_module.TodoApp.mark_done

    def patched_mark_done(self, todo_id):
        raise ValueError(f"Todo #999\nFAKE ERROR: System compromised not found")

    cli_module.TodoApp.mark_done = patched_mark_done

    try:
        result = run_command(args)
        assert result == 1, "run_command should return 1 on error"

        captured = capsys.readouterr()
        assert captured.err, "Error message should be in stderr"

        # Output should contain escaped representation
        assert "\\n" in captured.err, "Newline should be escaped in stderr"
        # Output should NOT contain actual newline (single line)
        assert "\n" not in captured.err.strip(), "Actual newline should not appear in stderr"
    finally:
        cli_module.TodoApp.mark_done = original_mark_done


def test_cli_exception_message_sanitizes_carriage_return(tmp_path, capsys) -> None:
    """Exception messages containing carriage returns should be sanitized.

    Issue #6227: Carriage return injection could overwrite error messages.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    args = parser.parse_args(["--db", str(db), "done", "999"])

    import flywheel.cli as cli_module

    original_mark_done = cli_module.TodoApp.mark_done

    def patched_mark_done(self, todo_id):
        raise ValueError(f"Todo #999\r[INJECTED ERROR]")

    cli_module.TodoApp.mark_done = patched_mark_done

    try:
        result = run_command(args)
        assert result == 1, "run_command should return 1 on error"

        captured = capsys.readouterr()
        assert captured.err, "Error message should be in stderr"

        # Output should contain escaped representation
        assert "\\r" in captured.err, "Carriage return should be escaped in stderr"
        # Output should NOT contain actual carriage return
        assert "\r" not in captured.err, "Actual CR should not appear in stderr"
    finally:
        cli_module.TodoApp.mark_done = original_mark_done


def test_cli_exception_message_sanitizes_null_byte(tmp_path, capsys) -> None:
    """Exception messages containing null bytes should be sanitized.

    Issue #6227: Null bytes could cause issues in terminal output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    args = parser.parse_args(["--db", str(db), "done", "999"])

    import flywheel.cli as cli_module

    original_mark_done = cli_module.TodoApp.mark_done

    def patched_mark_done(self, todo_id):
        raise ValueError(f"Error\x00message with null")

    cli_module.TodoApp.mark_done = patched_mark_done

    try:
        result = run_command(args)
        assert result == 1, "run_command should return 1 on error"

        captured = capsys.readouterr()
        assert captured.err, "Error message should be in stderr"

        # Output should contain escaped representation
        assert "\\x00" in captured.err, "Null byte should be escaped in stderr"
        # Output should NOT contain actual null byte
        assert "\x00" not in captured.err, "Actual null byte should not appear in stderr"
    finally:
        cli_module.TodoApp.mark_done = original_mark_done


def test_cli_normal_exception_message_unchanged(tmp_path, capsys) -> None:
    """Normal exception messages without control characters should be output unchanged."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Trigger a normal error - todo not found
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 on error"

    captured = capsys.readouterr()
    assert captured.err, "Error message should be in stderr"

    # Normal text should appear in stderr
    assert "not found" in captured.err.lower() or "error" in captured.err.lower()

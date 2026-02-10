"""Regression tests for Issue #2083: CLI outputs user-supplied todo.text without sanitization in success messages.

This test file ensures that CLI success messages (add, done, undone) sanitize control
characters in todo.text before outputting to stdout to prevent terminal control
character injection attacks.

Issue #2083 specifically highlights lines 98, 108, 113 in cli.py where todo.text
is displayed in success messages.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_add_command_sanitizes_ansi_escape_in_success_message(tmp_path, capsys) -> None:
    """add command should escape ANSI escape sequences in success message.

    Issue #2083: Line 98 prints todo.text without sanitization, allowing terminal
    control character injection via ANSI escape sequences like \\x1b[31m.
    """
    db = "test-ansi-success.json"
    parser = build_parser()
    # ANSI escape sequence that would make text red if not sanitized
    args = parser.parse_args(["--db", db, "add", "\x1b[31mRed Text\x1b[0m Normal"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\x1b" in captured.out
    # Output should NOT contain actual ESC character (prevents terminal injection)
    assert "\x1b" not in captured.out

    # Clean up
    from pathlib import Path
    Path(db).unlink(missing_ok=True)


def test_cli_done_command_sanitizes_carriage_return_in_success_message(tmp_path, capsys) -> None:
    """done command should escape carriage returns in success message.

    Issue #2083: Line 108 prints todo.text without sanitization, allowing
    carriage return injection that could overwrite output.
    """
    db = "test-carriage-success.json"
    parser = build_parser()

    # First add a todo with carriage return
    add_args = parser.parse_args(["--db", db, "add", "Valid task\r[INJECTED]"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Now mark it as done
    done_args = parser.parse_args(["--db", db, "done", "1"])
    result = run_command(done_args)
    assert result == 0, "done command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation (visible as literal \r)
    assert "\\r" in captured.out
    # Output should NOT contain actual carriage return (prevents output overwrite)
    assert "\r" not in captured.out
    # After sanitization, the injected text is visible (escaped), not rendered
    # This is expected - the control character is neutralized
    assert "\\r[INJECTED]" in captured.out

    # Clean up
    from pathlib import Path
    Path(db).unlink(missing_ok=True)


def test_cli_undone_command_sanitizes_newline_in_success_message(tmp_path, capsys) -> None:
    """undone command should escape newlines in success message.

    Issue #2083: Line 113 prints todo.text without sanitization, allowing
    newline injection that could create fake todos in output.
    """
    db = "test-newline-success.json"
    parser = build_parser()

    # First add and mark done a todo with newline injection
    add_args = parser.parse_args(["--db", db, "add", "Buy milk\n[ ] FAKE_TODO"])
    run_command(add_args)
    done_args = parser.parse_args(["--db", db, "done", "1"])
    run_command(done_args)
    capsys.readouterr()  # Clear previous output

    # Now mark it as undone
    undone_args = parser.parse_args(["--db", db, "undone", "1"])
    result = run_command(undone_args)
    assert result == 0, "undone command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation (visible as literal \n)
    assert "\\n" in captured.out
    # Output should NOT contain actual newline (single line output, prevents fake todos)
    assert "\n" not in captured.out.strip()
    # After sanitization, the fake todo text is visible (escaped), not rendered
    # This is expected - the control character is neutralized
    assert "\\n[ ] FAKE_TODO" in captured.out

    # Clean up
    from pathlib import Path
    Path(db).unlink(missing_ok=True)


def test_cli_all_commands_use_sanitize_text(tmp_path, capsys) -> None:
    """All CLI success messages should use _sanitize_text for user output.

    Issue #2083 acceptance criteria: Terminal control characters in todo text
    are escaped in CLI output for add, done, and undone commands.
    """
    db = "test-all-sanitize.json"
    parser = build_parser()

    # Test add command with multiple control characters
    add_args = parser.parse_args(["--db", db, "add", "Task\n\r\tWith\x00Controls"])
    run_command(add_args)
    captured = capsys.readouterr()
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    assert "\\t" in captured.out
    assert "\\x00" in captured.out
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
    assert "\x00" not in captured.out

    # Test done command
    done_args = parser.parse_args(["--db", db, "done", "1"])
    run_command(done_args)
    captured = capsys.readouterr()
    assert "\\n" in captured.out
    assert "\n" not in captured.out.strip()

    # Test undone command
    undone_args = parser.parse_args(["--db", db, "undone", "1"])
    run_command(undone_args)
    captured = capsys.readouterr()
    assert "\\n" in captured.out
    assert "\n" not in captured.out.strip()

    # Clean up
    from pathlib import Path
    Path(db).unlink(missing_ok=True)

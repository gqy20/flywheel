"""Regression tests for Issue #2084: CLI commands sanitize control characters.

This test file ensures that CLI commands (add, done, undone) sanitize
todo.text before outputting to stdout to prevent terminal control character
injection attacks.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_add_command_sanitizes_newline(tmp_path, capsys) -> None:
    """add command should escape \\n in todo text to prevent fake todo injection."""
    db = tmp_path / "test.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "Buy milk\n[ ] FAKE_TODO"])

    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    # Should not contain actual newline (no multi-line output)
    assert "\n" not in captured.out or captured.out.count("\n") <= 1
    # Should show the full escaped string, not inject fake todo
    assert "Buy milk\\n[ ] FAKE_TODO" in captured.out


def test_cli_done_command_sanitizes_carriage_return(tmp_path, capsys) -> None:
    """done command should escape \\r in todo text to prevent line overwriting."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # First add a todo with carriage return
    args = parser.parse_args(["--db", str(db), "add", "Valid task\r[ ] FAKE"])
    run_command(args)
    capsys.readouterr()  # Clear output

    # Now mark it as done
    args = parser.parse_args(["--db", str(db), "done", "1"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\r" in captured.out
    # Should not contain actual carriage return
    assert "\r" not in captured.out


def test_cli_undone_command_sanitizes_tab(tmp_path, capsys) -> None:
    """undone command should escape \\t in todo text."""
    db = tmp_path / "test.json"
    parser = build_parser()

    # First add and complete a todo with tab
    args = parser.parse_args(["--db", str(db), "add", "Task\twith\ttabs"])
    run_command(args)
    capsys.readouterr()  # Clear output

    args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(args)
    capsys.readouterr()  # Clear output

    # Now mark it as undone
    args = parser.parse_args(["--db", str(db), "undone", "1"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\t" in captured.out
    # Should not contain actual tab character
    assert "\t" not in captured.out


def test_cli_add_command_sanitizes_ansi_escape_codes(tmp_path, capsys) -> None:
    """add command should escape ANSI escape sequences to prevent terminal injection."""
    db = tmp_path / "test.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "\x1b[31mRed Text\x1b[0m Normal"])

    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\x1b" in captured.out
    # Should not contain actual ESC character
    assert "\x1b" not in captured.out


def test_cli_add_command_normal_text_unchanged(tmp_path, capsys) -> None:
    """Normal todo text without control characters should be unchanged."""
    db = tmp_path / "test.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "Buy groceries"])

    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    # Should contain normal text unchanged
    assert "Buy groceries" in captured.out
    # Should not contain escape sequences
    assert "\\n" not in captured.out
    assert "\\r" not in captured.out
    assert "\\t" not in captured.out

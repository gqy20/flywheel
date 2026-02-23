"""Regression tests for Issue #2084: CLI commands output unsanitized todo.text.

This test file ensures that CLI commands (add, done, undone) sanitize control
characters in todo.text before outputting to stdout to prevent terminal control
character injection attacks.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_add_command_sanitizes_newline_in_output(tmp_path, capsys) -> None:
    """add command should escape newlines in todo text output.

    When adding a todo with control characters like \\n, the stdout output
    should contain escaped representation (\\n) not actual newline.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "Buy milk\n[ ] FAKE_TODO"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    # Output should NOT contain actual newline character (single line output)
    assert "\n" not in captured.out.strip()


def test_cli_add_command_sanitizes_carriage_return_in_output(tmp_path, capsys) -> None:
    """add command should escape carriage returns in todo text output."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "Valid task\r[ ] FAKE"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\r" in captured.out
    # Output should NOT contain actual carriage return
    assert "\r" not in captured.out


def test_cli_add_command_sanitizes_tab_in_output(tmp_path, capsys) -> None:
    """add command should escape tabs in todo text output."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "Task\twith\ttabs"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\t" in captured.out
    # Output should NOT contain actual tab character
    assert "\t" not in captured.out


def test_cli_done_command_sanitizes_newline_in_output(tmp_path, capsys) -> None:
    """done command should escape newlines in todo text output.

    When marking a todo with control characters as done, the stdout output
    should contain escaped representation (\\n) not actual newline.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo with newline
    add_args = parser.parse_args(["--db", str(db), "add", "Buy milk\n[ ] FAKE_TODO"])
    run_command(add_args)

    # Clear captured output from add
    capsys.readouterr()

    # Now mark it as done
    done_args = parser.parse_args(["--db", str(db), "done", "1"])
    result = run_command(done_args)
    assert result == 0, "done command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    # Output should NOT contain actual newline character
    assert "\n" not in captured.out.strip()


def test_cli_done_command_sanitizes_carriage_return_in_output(tmp_path, capsys) -> None:
    """done command should escape carriage returns in todo text output."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo with carriage return
    add_args = parser.parse_args(["--db", str(db), "add", "Valid task\r[ ] FAKE"])
    run_command(add_args)

    # Clear captured output from add
    capsys.readouterr()

    # Now mark it as done
    done_args = parser.parse_args(["--db", str(db), "done", "1"])
    result = run_command(done_args)
    assert result == 0, "done command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\r" in captured.out
    # Output should NOT contain actual carriage return
    assert "\r" not in captured.out


def test_cli_undone_command_sanitizes_newline_in_output(tmp_path, capsys) -> None:
    """undone command should escape newlines in todo text output.

    When marking a todo with control characters as undone, the stdout output
    should contain escaped representation (\\n) not actual newline.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add and mark as done a todo with newline
    add_args = parser.parse_args(["--db", str(db), "add", "Buy milk\n[ ] FAKE_TODO"])
    run_command(add_args)
    done_args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(done_args)

    # Clear captured output
    capsys.readouterr()

    # Now mark it as undone
    undone_args = parser.parse_args(["--db", str(db), "undone", "1"])
    result = run_command(undone_args)
    assert result == 0, "undone command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    # Output should NOT contain actual newline character
    assert "\n" not in captured.out.strip()


def test_cli_undone_command_sanitizes_tab_in_output(tmp_path, capsys) -> None:
    """undone command should escape tabs in todo text output."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add and mark as done a todo with tab
    add_args = parser.parse_args(["--db", str(db), "add", "Task\twith\ttabs"])
    run_command(add_args)
    done_args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(done_args)

    # Clear captured output
    capsys.readouterr()

    # Now mark it as undone
    undone_args = parser.parse_args(["--db", str(db), "undone", "1"])
    result = run_command(undone_args)
    assert result == 0, "undone command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\t" in captured.out
    # Output should NOT contain actual tab character
    assert "\t" not in captured.out


def test_cli_add_command_sanitizes_ansi_escape_sequences(tmp_path, capsys) -> None:
    """add command should escape ANSI escape sequences to prevent terminal injection.

    ANSI escape sequences like \\x1b[31m could be used to manipulate terminal
    output or hide fake todos.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "\x1b[31mRed Text\x1b[0m Normal"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\x1b" in captured.out
    # Output should NOT contain actual ESC character
    assert "\x1b" not in captured.out


def test_cli_add_command_sanitizes_null_byte(tmp_path, capsys) -> None:
    """add command should escape null bytes."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "Before\x00After"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\x00" in captured.out
    # Output should NOT contain actual null byte
    assert "\x00" not in captured.out


def test_cli_add_command_normal_text_unchanged(tmp_path, capsys) -> None:
    """Normal todo text without control characters should output unchanged."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "Buy groceries"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Normal text should be output as-is
    assert "Buy groceries" in captured.out


def test_cli_add_command_with_unicode_passes_through(tmp_path, capsys) -> None:
    """Unicode characters should pass through unchanged in CLI output."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "Buy café and 日本語"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Unicode should be preserved
    assert "café" in captured.out
    assert "日本語" in captured.out


def test_cli_add_command_sanitizes_bidi_rlo(tmp_path, capsys) -> None:
    """add command should escape Bidi RLO (U+202E) to prevent text spoofing.

    The RLO (Right-to-Left Override) character can be used to reverse text
    direction, causing terminal display to differ from actual content.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "Hello\u202eWorld"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\u202e" in captured.out
    # Output should NOT contain actual RLO character
    assert "\u202e" not in captured.out


def test_cli_add_command_sanitizes_bidi_lro(tmp_path, capsys) -> None:
    """add command should escape Bidi LRO (U+202D) to prevent text spoofing.

    The LRO (Left-to-Right Override) character can force text direction.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "Test\u202dValue"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\u202d" in captured.out
    # Output should NOT contain actual LRO character
    assert "\u202d" not in captured.out


def test_cli_add_command_sanitizes_bidi_pdi(tmp_path, capsys) -> None:
    """add command should escape Bidi PDI (U+2069) to prevent text spoofing.

    The PDI (Pop Directional Isolate) character is part of Bidi isolate pairs.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "Start\u2069End"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\u2069" in captured.out
    # Output should NOT contain actual PDI character
    assert "\u2069" not in captured.out


def test_cli_add_command_sanitizes_bidi_lrm(tmp_path, capsys) -> None:
    """add command should escape Bidi LRM (U+200E) to prevent text spoofing.

    The LRM (Left-to-Right Mark) is an invisible formatting character.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "A\u200eB"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\u200e" in captured.out
    # Output should NOT contain actual LRM character
    assert "\u200e" not in captured.out


def test_cli_add_command_sanitizes_bidi_rlm(tmp_path, capsys) -> None:
    """add command should escape Bidi RLM (U+200F) to prevent text spoofing.

    The RLM (Right-to-Left Mark) is an invisible formatting character.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "X\u200fY"])

    result = run_command(args)
    assert result == 0, "add command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\u200f" in captured.out
    # Output should NOT contain actual RLM character
    assert "\u200f" not in captured.out

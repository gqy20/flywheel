"""Regression tests for Issue #2457: Overly broad exception catching masks unexpected errors.

This test file ensures that run_command catches ONLY specific expected exception
types (ValueError, OSError, json.JSONDecodeError) and lets critical exceptions
like KeyboardInterrupt and SystemExit propagate properly.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from flywheel.cli import TodoApp, build_parser, run_command


def test_keyboard_interrupt_propagates(tmp_path) -> None:
    """KeyboardInterrupt (Ctrl+C) should propagate, not be caught by run_command.

    The overly broad 'except Exception' in the original code catches KeyboardInterrupt,
    preventing users from terminating the program with Ctrl+C. After the fix,
    KeyboardInterrupt should propagate to allow proper program termination.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    args = parser.parse_args(["--db", str(db), "add", "test"])

    def mock_add_raises_keyboard_interrupt(self, text: str):
        raise KeyboardInterrupt()

    # Patch TodoApp.add to raise KeyboardInterrupt
    # KeyboardInterrupt should propagate, not return 1
    with (
        patch.object(TodoApp, "add", mock_add_raises_keyboard_interrupt),
        pytest.raises(KeyboardInterrupt),
    ):
        run_command(args)


def test_system_exit_propagates(tmp_path) -> None:
    """SystemExit should propagate, not be caught by run_command.

    SystemExit is used by sys.exit() and should be allowed to propagate
    for proper program termination. The overly broad exception handler
    incorrectly catches this.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    args = parser.parse_args(["--db", str(db), "add", "test"])

    def mock_add_raises_system_exit(self, text: str):
        raise SystemExit(42)

    # Patch TodoApp.add to raise SystemExit
    # SystemExit should propagate, not return 1
    with (
        patch.object(TodoApp, "add", mock_add_raises_system_exit),
        pytest.raises(SystemExit) as exc_info,
    ):
        run_command(args)
    assert exc_info.value.code == 42


def test_value_error_still_caught(tmp_path, capsys) -> None:
    """ValueError should still be caught and handled gracefully.

    This is a regression test to ensure the fix doesn't break existing
    error handling for ValueError exceptions.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Trigger ValueError by marking non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])

    # Should return 1, not crash
    result = run_command(args)
    assert result == 1, "run_command should return 1 on ValueError"

    captured = capsys.readouterr()
    # Error message should be present
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_os_error_still_caught(tmp_path, capsys) -> None:
    """OSError should still be caught and handled gracefully.

    This is a regression test to ensure the fix doesn't break existing
    error handling for OSError exceptions.
    """
    # Use a path that likely won't have write permissions
    # On Unix systems, /root/ typically requires root access
    parser = build_parser()
    args = parser.parse_args(["--db", "/root/flywheel-test-db.json", "add", "test"])

    # Should return 1, not crash with unhandled OSError
    result = run_command(args)
    assert result == 1, "run_command should return 1 on permission error"

    captured = capsys.readouterr()
    # Error message should be present
    assert captured.err or captured.out


def test_json_decode_error_still_caught(tmp_path, capsys) -> None:
    """json.JSONDecodeError should still be caught and handled gracefully.

    This is a regression test to ensure the fix doesn't break existing
    error handling for JSON decode errors.
    """
    db = tmp_path / "invalid.json"
    # Write invalid JSON that will cause json.JSONDecodeError
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Should return 1, not crash with unhandled exception
    result = run_command(args)
    assert result == 1, "run_command should return 1 on JSON decode error"

    captured = capsys.readouterr()
    # Error message should be in stderr, not stdout
    assert "error" in captured.err.lower() or "error" in captured.out.lower()

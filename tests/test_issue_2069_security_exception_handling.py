"""Regression tests for Issue #2069: Security - Critical exceptions must propagate.

This test file ensures that run_command does NOT catch critical exceptions
like KeyboardInterrupt and SystemExit, which should always propagate to allow
proper program termination.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from flywheel.cli import build_parser, run_command


def test_cli_run_command_does_not_catch_keyboardinterrupt(tmp_path) -> None:
    """KeyboardInterrupt must NOT be caught by run_command.

    When Ctrl+C is pressed (SIGINT), the program should exit immediately
    by allowing KeyboardInterrupt to propagate. This is a security requirement.
    """
    db = tmp_path / "db.json"

    def mock_load_that_raises_keyboard_interrupt(self):
        raise KeyboardInterrupt()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Patch TodoStorage.load to raise KeyboardInterrupt
    with (
        patch("flywheel.cli.TodoStorage.load", mock_load_that_raises_keyboard_interrupt),
        pytest.raises(KeyboardInterrupt),
    ):
        run_command(args)


def test_cli_run_command_does_not_catch_system_exit(tmp_path) -> None:
    """SystemExit must NOT be caught by run_command.

    SystemExit is used by argparse and the program itself to control
    exit flow. It should never be caught as a generic exception.
    """
    db = tmp_path / "db.json"

    def mock_load_that_raises_system_exit(self):
        raise SystemExit(42)

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Patch TodoStorage.load to raise SystemExit
    with (
        patch("flywheel.cli.TodoStorage.load", mock_load_that_raises_system_exit),
        pytest.raises(SystemExit) as exc_info,
    ):
        run_command(args)
        # Verify the exit code is preserved
        assert exc_info.value.code == 42


def test_cli_run_command_still_catches_value_error(tmp_path, capsys) -> None:
    """ValueError SHOULD still be caught by run_command.

    This verifies that business logic errors (like "todo not found")
    are still handled gracefully while allowing critical errors to propagate.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    # Trigger a ValueError by trying to mark non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])

    # Should return 1, NOT raise ValueError
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()


def test_cli_run_command_still_catches_os_error(tmp_path, capsys) -> None:
    """OSError SHOULD still be caught by run_command.

    This verifies that file system errors are still handled gracefully
    while allowing critical errors to propagate.
    """
    # Create a directory at the db path to trigger OSError when trying to write
    db = tmp_path / "blocking-dir"
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    # Should return 1, NOT raise OSError
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # Error message should be in stderr
    assert captured.err


def test_cli_run_command_still_catches_json_decode_error_via_value(tmp_path, capsys) -> None:
    """json.JSONDecodeError SHOULD still be caught (it's a ValueError subclass).

    This verifies that JSON parsing errors are still handled gracefully.
    """
    db = tmp_path / "invalid.json"
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Should return 1, NOT raise json.JSONDecodeError
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "invalid" in captured.err.lower()

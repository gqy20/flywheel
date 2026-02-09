"""Regression tests for Issue #2457: Overly broad exception catching masks unexpected errors.

This test file ensures that run_command only catches expected exception types
and allows unexpected exceptions (KeyboardInterrupt, SystemExit) to propagate.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from flywheel.cli import build_parser, run_command


def test_cli_keyboard_interrupt_propagates(tmp_path) -> None:
    """KeyboardInterrupt should propagate, not be caught by Exception handler.

    When the user presses Ctrl+C, the program should terminate immediately
    via KeyboardInterrupt, not return 1 and continue execution.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock the load method to raise KeyboardInterrupt (simulating Ctrl+C)
    with (
        patch("flywheel.cli.TodoApp._load", side_effect=KeyboardInterrupt()),
        pytest.raises(KeyboardInterrupt),
    ):
        run_command(args)


def test_cli_system_exit_propagates(tmp_path) -> None:
    """SystemExit should propagate and not be caught by Exception handler.

    SystemExit is used for explicit program termination and should not
    be caught by general exception handlers.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock the load method to raise SystemExit
    with patch("flywheel.cli.TodoApp._load", side_effect=SystemExit(42)):
        # Should raise SystemExit, not return 1
        with pytest.raises(SystemExit) as exc_info:
            run_command(args)
        # The exit code should be preserved
        assert exc_info.value.code == 42


def test_cli_expected_value_error_still_caught(tmp_path, capsys) -> None:
    """ValueError should still be caught and handled gracefully."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Trigger ValueError by marking non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])
    result = run_command(args)

    assert result == 1, "run_command should return 1 on ValueError"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_expected_os_error_still_caught(tmp_path, capsys) -> None:
    """OSError should still be caught and handled gracefully."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Create a directory at the db path to trigger OSError
    db.mkdir()

    args = parser.parse_args(["--db", str(db), "add", "test"])
    result = run_command(args)

    assert result == 1, "run_command should return 1 on OSError"
    captured = capsys.readouterr()
    # Some error message should be present
    assert captured.err or captured.out


def test_cli_expected_json_decode_error_still_caught(tmp_path, capsys) -> None:
    """json.JSONDecodeError should still be caught and handled gracefully."""
    db = tmp_path / "invalid.json"
    # Write invalid JSON that will cause json.JSONDecodeError
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 on JSON decode error"

    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "error" in captured.out.lower()


def test_cli_unexpected_exception_propagates(tmp_path) -> None:
    """Unexpected exceptions (not ValueError/OSError/JSONDecodeError) should propagate.

    This is a design choice: unexpected errors should crash visibly
    rather than being silently converted to return code 1.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock to raise an unexpected exception type
    class UnexpectedError(Exception):
        pass

    with (
        patch("flywheel.cli.TodoApp._load", side_effect=UnexpectedError("boom")),
        pytest.raises(UnexpectedError, match="boom"),
    ):
        run_command(args)

"""Regression tests for Issue #2457: Overly broad exception catching.

This test file ensures that KeyboardInterrupt propagates properly (allowing
Ctrl+C to work) while still catching expected exceptions like ValueError,
OSError, and json.JSONDecodeError.
"""

from __future__ import annotations

import pytest

from flywheel.cli import build_parser, run_command


def test_cli_keyboard_interrupt_propagates(tmp_path) -> None:
    """KeyboardInterrupt should propagate, not be caught by Exception handler.

    When user presses Ctrl+C (KeyboardInterrupt), it should propagate
    instead of being caught and returning 1. This allows proper
    program termination.
    """
    from unittest.mock import patch

    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock list() to raise KeyboardInterrupt (simulates Ctrl+C during list operation)
    with pytest.raises(KeyboardInterrupt), patch(
        "flywheel.cli.TodoApp.list", side_effect=KeyboardInterrupt()
    ):
        run_command(args)


def test_cli_system_exit_propagates(tmp_path) -> None:
    """SystemExit should propagate for proper exit handling."""
    from unittest.mock import patch

    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock list() to raise SystemExit
    with pytest.raises(SystemExit), patch(
        "flywheel.cli.TodoApp.list", side_effect=SystemExit(0)
    ):
        run_command(args)


def test_cli_expected_value_error_still_caught(tmp_path, capsys) -> None:
    """ValueError should still be caught and handled gracefully."""
    db = tmp_path / "db.json"

    # Try to mark a non-existent todo as done (raises ValueError)
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 for ValueError"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_expected_os_error_still_caught(tmp_path, capsys) -> None:
    """OSError should still be caught and handled gracefully."""
    # Create a directory at the db path to trigger OSError
    db = tmp_path / "db.json"
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 for OSError"

    captured = capsys.readouterr()
    assert captured.err or captured.out


def test_cli_expected_json_decode_error_still_caught(tmp_path, capsys) -> None:
    """json.JSONDecodeError should still be caught and handled gracefully."""
    db = tmp_path / "invalid.json"
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 for JSONDecodeError"

    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "error" in captured.out.lower()


def test_cli_unexpected_runtime_error_propagates(tmp_path) -> None:
    """Unexpected exceptions like RuntimeError should propagate for debugging.

    This test ensures that the fix (catching only specific exception types)
    allows unexpected errors to propagate, making debugging easier.
    """
    from unittest.mock import patch

    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # RuntimeError should propagate (not caught by specific exception handlers)
    with pytest.raises(RuntimeError, match="unexpected error"), patch(
        "flywheel.cli.TodoApp.list", side_effect=RuntimeError("unexpected error")
    ):
        run_command(args)

"""Regression tests for Issue #3320: Broad Exception catch should be specific.

This test file ensures that run_command catches only expected exception types
(ValueError, OSError, json.JSONDecodeError) rather than catching all Exception
subclasses. Unexpected exceptions should propagate to avoid hiding bugs.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from flywheel.cli import build_parser, run_command


def test_cli_propagates_keyboard_interrupt(tmp_path) -> None:
    """KeyboardInterrupt should propagate, not be caught by exception handler.

    This test ensures that Ctrl+C (KeyboardInterrupt) immediately terminates
    the CLI without printing an error message.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    with (
        patch("flywheel.cli.TodoApp.add", side_effect=KeyboardInterrupt),
        pytest.raises(KeyboardInterrupt),
    ):
        run_command(args)


def test_cli_propagates_system_exit(tmp_path) -> None:
    """SystemExit should propagate, not be caught by exception handler.

    This test ensures that SystemExit propagates correctly for proper exit
    handling.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    with (
        patch("flywheel.cli.TodoApp.add", side_effect=SystemExit(42)),
        pytest.raises(SystemExit),
    ):
        run_command(args)


def test_cli_catches_value_error_gracefully(tmp_path, capsys) -> None:
    """ValueError should be caught and handled gracefully.

    ValueError is raised by business logic (e.g., empty todo text, todo not found)
    and should be caught and formatted as an error message.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "not found" in captured.err.lower()


def test_cli_catches_os_error_gracefully(tmp_path, capsys) -> None:
    """OSError should be caught and handled gracefully.

    OSError is raised when file operations fail (permissions, disk full, etc.)
    and should be caught and formatted as an error message.
    """
    # Use a path that likely won't have write permissions
    parser = build_parser()
    args = parser.parse_args(["--db", "/root/flywheel-test-db-3320.json", "add", "test"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # Error message should be present in stderr
    assert captured.err


def test_cli_catches_json_decode_error_gracefully(tmp_path, capsys) -> None:
    """json.JSONDecodeError should be caught and handled gracefully.

    json.JSONDecodeError is raised when the database file contains invalid JSON
    and should be caught and formatted as an error message.
    """
    db = tmp_path / "invalid.json"
    # Write invalid JSON that will cause json.JSONDecodeError
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "error" in captured.out.lower()


def test_cli_propagates_unexpected_runtime_error(tmp_path) -> None:
    """Unexpected RuntimeError should propagate, not be silently caught.

    This test ensures that unexpected exceptions that indicate bugs in the code
    are not silently swallowed by a too-broad exception handler.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    with (
        patch("flywheel.cli.TodoApp.add", side_effect=RuntimeError("unexpected bug")),
        pytest.raises(RuntimeError, match="unexpected bug"),
    ):
        run_command(args)

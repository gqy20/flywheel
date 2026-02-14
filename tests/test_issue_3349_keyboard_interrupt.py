"""Regression tests for Issue #3349: KeyboardInterrupt should not be caught.

This test file ensures that run_command does NOT catch KeyboardInterrupt
or other BaseException subclasses that should propagate normally.

The issue was that except Exception is too broad. While KeyboardInterrupt
is actually a BaseException (not Exception), the fix makes the exception
handling explicit by catching only specific business exceptions (ValueError,
OSError) to ensure no unintended exception swallowing can occur.
"""

from __future__ import annotations

import pytest

from flywheel.cli import build_parser, run_command


def test_cli_run_command_does_not_catch_keyboard_interrupt(tmp_path) -> None:
    """run_command should NOT catch KeyboardInterrupt.

    When a user presses Ctrl+C, the KeyboardInterrupt should propagate
    to the caller and not be silently swallowed.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock the app.list method to raise KeyboardInterrupt
    from unittest.mock import patch

    with patch("flywheel.cli.TodoApp") as mock_todo_app:
        mock_app = mock_todo_app.return_value
        mock_app.list.side_effect = KeyboardInterrupt("Ctrl+C pressed")

        # KeyboardInterrupt should propagate, NOT be caught
        with pytest.raises(KeyboardInterrupt):
            run_command(args)


def test_cli_run_command_does_not_catch_system_exit(tmp_path) -> None:
    """run_command should NOT catch SystemExit.

    SystemExit is a BaseException, not an Exception, and should propagate.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    from unittest.mock import patch

    with patch("flywheel.cli.TodoApp") as mock_todo_app:
        mock_app = mock_todo_app.return_value
        mock_app.list.side_effect = SystemExit(42)

        # SystemExit should propagate, NOT be caught
        with pytest.raises(SystemExit) as exc_info:
            run_command(args)

        assert exc_info.value.code == 42


def test_cli_run_command_still_catches_value_error(tmp_path, capsys) -> None:
    """run_command should still catch ValueError (business logic errors).

    This is a regression test to ensure we don't break existing behavior.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    # Should return 1, not raise
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_run_command_still_catches_os_error(tmp_path, capsys) -> None:
    """run_command should still catch OSError.

    This is a regression test to ensure we don't break existing behavior.
    """
    db = tmp_path / "db.json"
    # Create a directory at the db path to trigger OSError when trying to write
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    # Should return 1, not raise
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert captured.err or captured.out

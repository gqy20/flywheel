"""Regression tests for Issue #3349: run_command except Exception is too broad.

This test file ensures that run_command:
1. Does NOT catch KeyboardInterrupt (should propagate)
2. Does NOT catch SystemExit (should propagate)
3. Only catches expected application exceptions (ValueError, OSError)

The fix changes `except Exception` to catch specific exception types
(ValueError, OSError) that the application is designed to handle gracefully.
This makes the exception handling explicit and prevents accidentally catching
other Exception subclasses that should propagate.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.cli import build_parser, run_command


def test_cli_run_command_does_not_catch_keyboard_interrupt(tmp_path) -> None:
    """run_command should NOT catch KeyboardInterrupt.

    When KeyboardInterrupt (Ctrl+C) is raised during command execution,
    it should propagate up to the caller, not be swallowed.

    This is a regression test to ensure the exception handler only catches
    specific exception types (ValueError, OSError) and not all of Exception,
    which would include KeyboardInterrupt, SystemExit, etc.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock app.list to raise KeyboardInterrupt
    with patch("flywheel.cli.TodoApp") as mock_app_class:
        mock_app = mock_app_class.return_value
        mock_app.list.side_effect = KeyboardInterrupt("User pressed Ctrl+C")

        # KeyboardInterrupt should propagate, not be caught
        try:
            run_command(args)
            # If we get here, the KeyboardInterrupt was caught (bug!)
            raise AssertionError("KeyboardInterrupt should have propagated, but run_command returned")
        except KeyboardInterrupt as e:
            # This is the expected behavior - KeyboardInterrupt propagates
            assert "Ctrl+C" in str(e) or "User pressed" in str(e)


def test_cli_run_command_does_not_catch_system_exit(tmp_path) -> None:
    """run_command should NOT catch SystemExit.

    SystemExit should propagate up to allow proper exit handling.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock app.list to raise SystemExit
    with patch("flywheel.cli.TodoApp") as mock_app_class:
        mock_app = mock_app_class.return_value
        mock_app.list.side_effect = SystemExit(42)

        # SystemExit should propagate, not be caught
        try:
            run_command(args)
            # If we get here, the SystemExit was caught (bug!)
            raise AssertionError("SystemExit should have propagated, but run_command returned")
        except SystemExit as e:
            # This is the expected behavior - SystemExit propagates
            assert e.code == 42


def test_cli_run_command_catches_value_error(tmp_path, capsys) -> None:
    """run_command should catch ValueError and return exit code 1."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    # Should catch ValueError and return 1
    result = run_command(args)
    assert result == 1, "run_command should return 1 on ValueError"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_run_command_catches_os_error(tmp_path, capsys) -> None:
    """run_command should catch OSError and return exit code 1."""
    # Use a path that likely won't have write permissions
    parser = build_parser()
    args = parser.parse_args(["--db", "/root/flywheel-test-db.json", "add", "test"])

    # Should return 1, not crash
    result = run_command(args)
    assert result == 1, "run_command should return 1 on OSError"

    captured = capsys.readouterr()
    assert captured.err or captured.out  # Some error message should be present

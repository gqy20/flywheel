"""Regression tests for Issue #3349: run_command except Exception too broad.

This test file ensures that run_command:
1. Does NOT catch KeyboardInterrupt (should propagate to allow Ctrl+C)
2. Does NOT catch SystemExit (should propagate)
3. Only catches specific business exceptions: ValueError, OSError
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.cli import build_parser, run_command


def test_cli_run_command_propagates_keyboard_interrupt(tmp_path) -> None:
    """run_command should NOT catch KeyboardInterrupt.

    When KeyboardInterrupt is raised (e.g., user presses Ctrl+C),
    it should propagate up, not be caught and converted to exit code 1.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    with patch("flywheel.cli.TodoApp") as mock_app_class:
        mock_app = mock_app_class.return_value
        # Simulate KeyboardInterrupt being raised during list operation
        mock_app.list.side_effect = KeyboardInterrupt("User pressed Ctrl+C")

        # KeyboardInterrupt should propagate, NOT be caught
        try:
            result = run_command(args)
            # If we get here, KeyboardInterrupt was incorrectly caught
            raise AssertionError(f"KeyboardInterrupt should propagate, but got result={result}")
        except KeyboardInterrupt as e:
            # This is the expected behavior - KeyboardInterrupt propagates
            assert str(e) == "User pressed Ctrl+C"


def test_cli_run_command_propagates_system_exit(tmp_path) -> None:
    """run_command should NOT catch SystemExit.

    When SystemExit is raised (e.g., sys.exit()), it should propagate up.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    with patch("flywheel.cli.TodoApp") as mock_app_class:
        mock_app = mock_app_class.return_value
        # Simulate SystemExit being raised
        mock_app.list.side_effect = SystemExit(42)

        # SystemExit should propagate, NOT be caught
        try:
            result = run_command(args)
            # If we get here, SystemExit was incorrectly caught
            raise AssertionError(f"SystemExit should propagate, but got result={result}")
        except SystemExit as e:
            # This is the expected behavior - SystemExit propagates
            assert e.code == 42


def test_cli_run_command_catches_value_error(tmp_path, capsys) -> None:
    """run_command should catch ValueError and return exit code 1."""
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    # This will raise ValueError: Todo #999 not found
    result = run_command(args)

    assert result == 1, "run_command should return 1 on ValueError"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_run_command_catches_os_error(tmp_path, capsys) -> None:
    """run_command should catch OSError and return exit code 1."""
    db = tmp_path / "db.json"
    # Create a directory at the db path to trigger OSError when trying to write
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)

    assert result == 1, "run_command should return 1 on OSError"
    captured = capsys.readouterr()
    # Some error message should be present
    assert captured.err or captured.out


def test_cli_run_command_propagates_type_error(tmp_path) -> None:
    """run_command should NOT catch TypeError - programming errors should propagate.

    This ensures that unexpected exceptions (like TypeError, RuntimeError) are not
    silently swallowed, which would hide programming bugs.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    with patch("flywheel.cli.TodoApp") as mock_app_class:
        mock_app = mock_app_class.return_value
        # Simulate a programming error (TypeError) being raised
        mock_app.list.side_effect = TypeError("Cannot iterate over None")

        # TypeError should propagate, NOT be caught
        try:
            result = run_command(args)
            # If we get here, TypeError was incorrectly caught
            raise AssertionError(f"TypeError should propagate, but got result={result}")
        except TypeError as e:
            # This is the expected behavior - TypeError propagates
            assert str(e) == "Cannot iterate over None"


def test_cli_run_command_propagates_runtime_error(tmp_path) -> None:
    """run_command should NOT catch RuntimeError - programming errors should propagate.

    This ensures that unexpected exceptions are not silently swallowed.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    with patch("flywheel.cli.TodoApp") as mock_app_class:
        mock_app = mock_app_class.return_value
        # Simulate a programming error (RuntimeError) being raised
        mock_app.list.side_effect = RuntimeError("Coroutine not awaited")

        # RuntimeError should propagate, NOT be caught
        try:
            result = run_command(args)
            # If we get here, RuntimeError was incorrectly caught
            raise AssertionError(f"RuntimeError should propagate, but got result={result}")
        except RuntimeError as e:
            # This is the expected behavior - RuntimeError propagates
            assert str(e) == "Coroutine not awaited"

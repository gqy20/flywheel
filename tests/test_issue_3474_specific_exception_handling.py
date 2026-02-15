"""Regression tests for Issue #3474: Specific exception handling.

This test file ensures that run_command distinguishes between:
1. Expected exceptions (ValueError, OSError) - standard error messages
2. Unexpected exceptions (AttributeError, TypeError, etc.) - warning prefix

The fix replaces the broad `except Exception` handler with specific catches.
"""

from __future__ import annotations

from unittest import mock

from flywheel.cli import build_parser, run_command


def test_cli_handles_value_error_with_standard_message(tmp_path, capsys) -> None:
    """ValueError from business logic should show standard error message.

    This is an expected exception, so no warning prefix needed.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    # Trigger ValueError by marking non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    # Should contain error message about not found
    assert "not found" in captured.err.lower()
    # Should NOT contain unexpected exception warning
    assert "unexpected" not in captured.err.lower()


def test_cli_handles_os_error_with_standard_message(tmp_path, capsys) -> None:
    """OSError from file operations should show standard error message.

    This is an expected exception, so no warning prefix needed.
    """
    db = tmp_path / "malformed.json"
    # Create a directory at the db path to trigger OSError when trying to write
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    # Should contain error message
    assert captured.err
    # Should NOT contain unexpected exception warning
    assert "unexpected" not in captured.err.lower()


def test_cli_handles_attribute_error_with_warning_prefix(tmp_path, capsys) -> None:
    """Unexpected AttributeError should include warning in error message.

    This indicates a programming bug and should be flagged differently.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    # Mock app.add to raise AttributeError (programming bug)
    with mock.patch("flywheel.cli.TodoApp") as mock_app_class:
        mock_app = mock.MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.add.side_effect = AttributeError("simulated bug")

        result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    # Should contain error message with unexpected warning
    assert "error" in captured.err.lower()
    assert "unexpected" in captured.err.lower()


def test_cli_handles_type_error_with_warning_prefix(tmp_path, capsys) -> None:
    """Unexpected TypeError should include warning in error message.

    This indicates a programming bug and should be flagged differently.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    # Mock app.add to raise TypeError (programming bug)
    with mock.patch("flywheel.cli.TodoApp") as mock_app_class:
        mock_app = mock.MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.add.side_effect = TypeError("simulated bug")

        result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    # Should contain error message with unexpected warning
    assert "error" in captured.err.lower()
    assert "unexpected" in captured.err.lower()


def test_cli_handles_runtime_error_with_warning_prefix(tmp_path, capsys) -> None:
    """Unexpected RuntimeError should include warning in error message.

    This indicates an unexpected issue and should be flagged differently.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    # Mock app.add to raise RuntimeError (unexpected)
    with mock.patch("flywheel.cli.TodoApp") as mock_app_class:
        mock_app = mock.MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.add.side_effect = RuntimeError("simulated error")

        result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    # Should contain error message with unexpected warning
    assert "error" in captured.err.lower()
    assert "unexpected" in captured.err.lower()

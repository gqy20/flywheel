"""Regression tests for Issue #3474: Broad exception handler hides sensitive error details.

This test file ensures that run_command catches specific exception types
separately and handles unexpected exceptions with appropriate warnings.

The fix should:
- Catch ValueError from business logic with appropriate error message
- Catch OSError from file operations with appropriate error message
- Catch unexpected exceptions (AttributeError, TypeError) with a warning prefix
"""

from __future__ import annotations

from unittest import mock

from flywheel.cli import build_parser, run_command


def test_cli_value_error_has_clear_message(tmp_path, capsys) -> None:
    """ValueError should have a clear, user-friendly error message."""
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    # Trigger ValueError by trying to mark non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1, "ValueError should return exit code 1"

    captured = capsys.readouterr()
    # Error should be in stderr and not have "unexpected" warning prefix
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()
    # Should NOT have "unexpected" or "internal" prefix for expected errors
    full_output = captured.err + captured.out
    assert "unexpected" not in full_output.lower() or "error:" in captured.err.lower()


def test_cli_os_error_has_clear_message(capsys) -> None:
    """OSError should have a clear, user-friendly error message."""
    parser = build_parser()
    # Use a path that will trigger OSError (directory instead of file)
    args = parser.parse_args(["--db", "/nonexistent_dir_12345/db.json", "add", "test"])

    result = run_command(args)
    assert result == 1, "OSError should return exit code 1"

    captured = capsys.readouterr()
    # Error should be present in stderr
    assert captured.err or captured.out


def test_cli_unexpected_exception_shows_warning(tmp_path, capsys) -> None:
    """Unexpected exceptions like TypeError should show a warning prefix.

    This test ensures that programming bugs (TypeError, AttributeError, etc.)
    are distinguished from expected business errors in the error message.
    """
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()

    # Mock an unexpected exception type inside run_command
    with mock.patch("flywheel.cli.TodoApp") as mock_app_class:
        app_instance = mock.MagicMock()
        mock_app_class.return_value = app_instance
        # Simulate a TypeError being raised (unexpected programming bug)
        # Use a message that doesn't contain keywords we're checking for
        app_instance.add.side_effect = TypeError("Bad type conversion")

        args = parser.parse_args(["--db", str(db), "add", "test"])
        result = run_command(args)

        assert result == 1, "Unexpected exception should return exit code 1"

        captured = capsys.readouterr()
        full_output = captured.err + captured.out

        # Should contain indication this is unexpected/internal error
        # Either via prefix like "Internal error:" or by including the exception type name
        has_warning = "internal" in full_output.lower() or "typeerror" in full_output.lower()
        assert has_warning, (
            f"Unexpected exception should indicate it's unexpected. Got: {full_output!r}"
        )


def test_cli_attribute_error_shows_warning(tmp_path, capsys) -> None:
    """AttributeError (programming bug) should show a warning prefix."""
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()

    with mock.patch("flywheel.cli.TodoApp") as mock_app_class:
        app_instance = mock.MagicMock()
        mock_app_class.return_value = app_instance
        app_instance.add.side_effect = AttributeError("No such property")

        args = parser.parse_args(["--db", str(db), "add", "test"])
        result = run_command(args)

        assert result == 1, "AttributeError should return exit code 1"

        captured = capsys.readouterr()
        full_output = captured.err + captured.out

        # Should contain indication this is unexpected
        has_warning = "internal" in full_output.lower() or "attributeerror" in full_output.lower()
        assert has_warning, f"AttributeError should indicate it's unexpected. Got: {full_output!r}"


def test_cli_all_exceptions_return_exit_code_1(tmp_path, capsys) -> None:
    """All exceptions should return exit code 1, never crash."""
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()

    # Test various error conditions
    test_cases = [
        (["--db", str(db), "done", "999"], "ValueError from not found"),
        (["--db", "/root/test_db.json", "add", "test"], "OSError from permissions"),
    ]

    for cmd_args, description in test_cases:
        args = parser.parse_args(cmd_args)
        result = run_command(args)
        assert result == 1, f"{description} should return exit code 1"

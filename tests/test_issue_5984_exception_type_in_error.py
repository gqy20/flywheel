"""Regression tests for Issue #5984: Exception type name in error output.

This test file ensures that unexpected exceptions include the exception type
name in the error output for debugging purposes.
"""

from __future__ import annotations

import unittest.mock

from flywheel.cli import build_parser, run_command


def test_cli_includes_exception_type_in_error_output(tmp_path, capsys) -> None:
    """Error output should include exception type name for debugging.

    When an unexpected exception occurs (e.g., TypeError, AttributeError),
    the error message should include the exception type name to help
    identify the root cause of the issue.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock storage.load to raise TypeError (an unexpected exception type)
    with unittest.mock.patch(
        "flywheel.cli.TodoStorage.load",
        side_effect=TypeError("unexpected type error"),
    ):
        result = run_command(args)

    assert result == 1, "run_command should return 1 on exception"

    captured = capsys.readouterr()
    # Error message should include the exception type name "TypeError"
    assert "TypeError" in captured.err, (
        f"Error output should include exception type 'TypeError', got: {captured.err}"
    )


def test_cli_includes_attribute_error_type_in_output(tmp_path, capsys) -> None:
    """Error output should include AttributeError type name."""
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock storage.load to raise AttributeError
    with unittest.mock.patch(
        "flywheel.cli.TodoStorage.load",
        side_effect=AttributeError("missing attribute"),
    ):
        result = run_command(args)

    assert result == 1, "run_command should return 1 on exception"

    captured = capsys.readouterr()
    # Error message should include the exception type name "AttributeError"
    assert "AttributeError" in captured.err, (
        f"Error output should include exception type 'AttributeError', got: {captured.err}"
    )


def test_cli_includes_runtime_error_type_in_output(tmp_path, capsys) -> None:
    """Error output should include RuntimeError type name."""
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock storage.load to raise RuntimeError
    with unittest.mock.patch(
        "flywheel.cli.TodoStorage.load",
        side_effect=RuntimeError("something went wrong"),
    ):
        result = run_command(args)

    assert result == 1, "run_command should return 1 on exception"

    captured = capsys.readouterr()
    # Error message should include the exception type name "RuntimeError"
    assert "RuntimeError" in captured.err, (
        f"Error output should include exception type 'RuntimeError', got: {captured.err}"
    )

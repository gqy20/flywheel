"""Regression tests for Issue #5984: Exception type should be logged.

This test file ensures that unexpected exceptions include exception type name
in error output for debugging purposes.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.cli import build_parser, run_command


def test_cli_error_output_includes_exception_type_name(tmp_path, capsys) -> None:
    """Error output should include the exception type name for debugging.

    When an unexpected exception occurs (e.g., TypeError, AttributeError),
    the error message should include the exception type name to help
    identify bugs vs expected errors.
    """
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock storage.load to raise TypeError (an unexpected exception)
    with patch("flywheel.cli.TodoStorage.load") as mock_load:
        mock_load.side_effect = TypeError("unexpected type error")

        result = run_command(args)
        assert result == 1, "run_command should return 1 on TypeError"

    captured = capsys.readouterr()
    # The error output should include the exception type name
    assert "TypeError" in captured.err, (
        f"Error output should include exception type name. Got: {captured.err}"
    )
    assert "unexpected type error" in captured.err


def test_cli_error_output_includes_exception_type_for_attribute_error(
    tmp_path, capsys
) -> None:
    """Error output should include exception type for AttributeError."""
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Mock storage.load to raise AttributeError (an unexpected exception)
    with patch("flywheel.cli.TodoStorage.load") as mock_load:
        mock_load.side_effect = AttributeError("missing attribute")

        result = run_command(args)
        assert result == 1, "run_command should return 1 on AttributeError"

    captured = capsys.readouterr()
    # The error output should include the exception type name
    assert "AttributeError" in captured.err, (
        f"Error output should include exception type name. Got: {captured.err}"
    )


def test_cli_value_error_output_includes_exception_type(tmp_path, capsys) -> None:
    """Even expected exceptions like ValueError should show their type."""
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    # Try to mark non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # Error output should include ValueError type
    assert "ValueError" in captured.err, (
        f"Error output should include exception type. Got: {captured.err}"
    )
    assert "not found" in captured.err.lower()

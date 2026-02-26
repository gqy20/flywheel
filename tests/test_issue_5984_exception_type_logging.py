"""Regression tests for Issue #5984: Exception type should be logged in error output.

This test file ensures that unexpected exceptions include the exception type name
in the error output for debugging purposes.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.cli import build_parser, run_command


def test_cli_exception_output_includes_type_name(tmp_path, capsys) -> None:
    """Error output should include the exception type name for debugging.

    When an unexpected exception occurs, the error message should include
    the exception class name (e.g., TypeError, AttributeError) to help
    developers identify the root cause.
    """
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Patch storage.load to raise an unexpected TypeError
    with patch("flywheel.cli.TodoStorage.load") as mock_load:
        mock_load.side_effect = TypeError("unexpected type error")

        result = run_command(args)
        assert result == 1, "run_command should return 1 on unexpected exception"

    captured = capsys.readouterr()
    # Error message should include the exception type name
    assert "TypeError" in captured.err, (
        f"Error output should include exception type name. Got stderr: {captured.err!r}"
    )


def test_cli_exception_output_includes_attribute_error_type(tmp_path, capsys) -> None:
    """Error output should include AttributeError type name."""
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    with patch("flywheel.cli.TodoStorage.load") as mock_load:
        mock_load.side_effect = AttributeError("missing attribute")

        result = run_command(args)
        assert result == 1

    captured = capsys.readouterr()
    assert "AttributeError" in captured.err, (
        f"Error output should include AttributeError type. Got stderr: {captured.err!r}"
    )


def test_cli_exception_output_includes_runtime_error_type(tmp_path, capsys) -> None:
    """Error output should include RuntimeError type name."""
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    with patch("flywheel.cli.TodoStorage.load") as mock_load:
        mock_load.side_effect = RuntimeError("runtime issue")

        result = run_command(args)
        assert result == 1

    captured = capsys.readouterr()
    assert "RuntimeError" in captured.err, (
        f"Error output should include RuntimeError type. Got stderr: {captured.err!r}"
    )

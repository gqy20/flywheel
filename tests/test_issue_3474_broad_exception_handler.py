"""Regression tests for Issue #3474: Broad exception handler hides sensitive error details.

This test file ensures that run_command distinguishes between:
- ValueError: Expected business logic errors (empty text, not found)
- OSError: File operation errors (permission denied, disk full)
- Unexpected exceptions: Potential programming bugs (AttributeError, TypeError)

Unexpected exceptions should include a warning that this might be a bug.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.cli import build_parser, run_command


def test_cli_value_error_has_specific_error_message(tmp_path, capsys) -> None:
    """ValueError should produce specific error message without warning prefix."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # ValueError should show specific error, NOT "Unexpected error" prefix
    assert "not found" in captured.err.lower()
    assert "unexpected" not in captured.err.lower()


def test_cli_os_error_has_specific_error_message(tmp_path, capsys) -> None:
    """OSError should produce specific error message without warning prefix."""
    # Use a directory as db path to trigger OSError
    db = tmp_path / "dir"
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # OSError should show specific error, NOT "Unexpected error" prefix
    assert captured.err
    assert "unexpected" not in captured.err.lower()


def test_cli_unexpected_exception_shows_warning_prefix(tmp_path, capsys) -> None:
    """Unexpected exceptions (TypeError, AttributeError) should show warning.

    This test verifies that unexpected programming bugs are clearly marked
    so users know to report them, rather than being confused about what went wrong.
    """
    parser = build_parser()
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "add", "test"])

    # Simulate an unexpected programming error (TypeError in this case)
    with patch("flywheel.cli.TodoApp.add", side_effect=TypeError("Simulated bug")):
        result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    # Unexpected errors should be clearly marked
    # The fix should add a warning indicator for non-ValueError/non-OSError exceptions
    assert "unexpected" in captured.err.lower(), (
        "Unexpected exceptions should be marked with 'Unexpected' prefix to help "
        "users identify potential bugs vs normal errors"
    )


def test_cli_attribute_error_shows_warning_prefix(tmp_path, capsys) -> None:
    """AttributeError should be marked as unexpected (likely programming bug)."""
    parser = build_parser()
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "add", "test"])

    # Simulate AttributeError (a common programming bug)
    with patch("flywheel.cli.TodoApp.add", side_effect=AttributeError("Simulated bug")):
        result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    # AttributeError should be clearly marked as unexpected
    assert "unexpected" in captured.err.lower(), (
        "AttributeError should be marked as 'Unexpected' to indicate potential bug"
    )


def test_cli_runtime_error_shows_warning_prefix(tmp_path, capsys) -> None:
    """RuntimeError should be marked as unexpected (likely programming bug)."""
    parser = build_parser()
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "add", "test"])

    # Simulate RuntimeError (a common programming bug)
    with patch("flywheel.cli.TodoApp.add", side_effect=RuntimeError("Simulated bug")):
        result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    # RuntimeError should be clearly marked as unexpected
    assert "unexpected" in captured.err.lower(), (
        "RuntimeError should be marked as 'Unexpected' to indicate potential bug"
    )

"""Regression tests for Issue #3979: run_command hides exception type in error output.

This test file ensures that error output includes the exception type name
for better debugging when run_command catches exceptions.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_error_output_includes_valueerror_type(tmp_path, capsys) -> None:
    """Error output should include 'ValueError' for ValueError exceptions."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Trigger a ValueError by marking non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()

    # Error output should include the exception type name 'ValueError'
    error_output = captured.err.lower()
    assert "valueerror" in error_output, (
        f"Error output should include 'ValueError' but got: {captured.err}"
    )


def test_cli_error_output_includes_oserror_type(tmp_path, capsys) -> None:
    """Error output should include 'OSError' for OSError exceptions."""
    db = tmp_path / "db.json"
    # Create a directory at the db path to trigger OSError when trying to write
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # Error output should include the exception type name (OSError or a subclass like
    # FileNotFoundError, IsADirectoryError, PermissionError)
    error_output = captured.err.lower()
    oserror_subclasses = [
        "oserror",
        "filenotfounderror",
        "permissionerror",
        "isadirectoryerror",
    ]
    has_oserror = any(exc in error_output for exc in oserror_subclasses)
    assert has_oserror, (
        f"Error output should include OSError or subclass name but got: {captured.err}"
    )


def test_cli_error_output_still_user_friendly(tmp_path, capsys) -> None:
    """Error output should remain user-friendly with readable format.

    Format should be: 'Error: ExceptionType: message'
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Trigger a ValueError
    args = parser.parse_args(["--db", str(db), "done", "999"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()

    # Should start with 'Error:' and contain both type and message
    assert captured.err.startswith("Error:"), (
        f"Error output should start with 'Error:' but got: {captured.err}"
    )
    # Should contain the original message
    assert "not found" in captured.err.lower(), (
        f"Error output should contain 'not found' but got: {captured.err}"
    )

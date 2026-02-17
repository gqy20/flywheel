"""Regression tests for Issue #3979: Exception type visibility in run_command.

This test file ensures that run_command includes exception type name in error
output for better debugging, as per the fix recommendation.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_run_command_shows_valueerror_type(tmp_path, capsys) -> None:
    """run_command should include ValueError type in error output.

    When a ValueError is raised, the error message should contain 'ValueError'
    to help users understand what kind of error occurred.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Trigger a ValueError by marking non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])
    result = run_command(args)

    assert result == 1, "run_command should return 1 on error"
    captured = capsys.readouterr()

    # Error output should include the exception type name
    error_output = captured.err or captured.out
    assert "ValueError" in error_output, (
        f"Error output should include 'ValueError' for better debugging. "
        f"Got: {error_output!r}"
    )


def test_cli_run_command_shows_oserror_type(tmp_path, capsys) -> None:
    """run_command should include OSError type in error output.

    When an OSError is raised, the error message should contain 'OSError'
    to help users understand what kind of error occurred.
    """
    db = tmp_path / "db.json"
    # Create a directory at the db path to trigger OSError when trying to write
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 on OSError"

    captured = capsys.readouterr()
    error_output = captured.err or captured.out

    # Error output should include the exception type name
    assert "OSError" in error_output or "IsADirectoryError" in error_output, (
        f"Error output should include 'OSError' (or subclass) for better debugging. "
        f"Got: {error_output!r}"
    )


def test_cli_run_command_exception_type_format(tmp_path, capsys) -> None:
    """run_command should format exception as 'TypeError: message'.

    Verify the general format includes the exception type name before the message.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Trigger an error by trying to remove non-existent todo
    args = parser.parse_args(["--db", str(db), "rm", "999"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    error_output = captured.err or captured.out

    # Error should follow format: "Error: ExceptionType: message"
    # The format should contain "ValueError" and "not found" in a structured way
    assert "ValueError" in error_output, (
        f"Error should include exception type. Got: {error_output!r}"
    )
    assert "not found" in error_output.lower(), (
        f"Error should include the original message. Got: {error_output!r}"
    )

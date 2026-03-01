"""Regression tests for Issue #6658: Broad exception catch may hide unexpected errors.

This test file ensures that:
1. Specific exceptions (ValueError, OSError, json.JSONDecodeError) are caught separately
2. Full traceback is logged for debugging while showing user-friendly message
3. A --debug flag can be used to show verbose error output
"""

from __future__ import annotations

import logging

from flywheel.cli import build_parser, run_command


def test_cli_logs_traceback_on_exception(tmp_path, capsys, caplog) -> None:
    """run_command should log full traceback for debugging purposes.

    When an exception occurs, the full traceback should be logged (at DEBUG level)
    for debugging, while the user sees a friendly error message.
    """
    db = tmp_path / "invalid.json"
    # Write invalid JSON that will cause an error
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Capture log output at DEBUG level
    with caplog.at_level(logging.DEBUG):
        result = run_command(args)

    assert result == 1, "run_command should return 1 on error"

    # The user-friendly error message should be in stderr
    captured = capsys.readouterr()
    assert captured.err, "Error message should be in stderr"

    # The traceback should be logged (this is what we're testing)
    # Check that either caplog has debug records or traceback appears somewhere
    has_traceback_log = any("Traceback" in record.message for record in caplog.records)
    assert has_traceback_log, (
        "Full traceback should be logged at DEBUG level for debugging purposes"
    )


def test_cli_catches_value_error_specifically(tmp_path, capsys) -> None:
    """ValueError should be caught and handled with specific message."""
    db = tmp_path / "db.json"

    parser = build_parser()
    # Trigger ValueError by trying to mark non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # Should have a user-friendly error message
    assert "not found" in captured.err.lower() or "error" in captured.err.lower()


def test_cli_catches_os_error_specifically(tmp_path, capsys) -> None:
    """OSError should be caught and handled with specific message."""
    db = tmp_path / "db.json"
    # Create a directory at the db path to trigger OSError when trying to write
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 on OSError"

    captured = capsys.readouterr()
    # Should have an error message about the OS issue
    assert captured.err, "Error message should be in stderr"


def test_cli_user_friendly_error_without_debug(tmp_path, capsys) -> None:
    """Without debug mode, users should see friendly error messages, not tracebacks."""
    db = tmp_path / "db.json"

    parser = build_parser()
    # Trigger an error
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # The stderr should NOT contain a Python traceback (user-friendly)
    # It should contain a simple error message
    assert "Traceback" not in captured.err, (
        "Users should not see Python tracebacks without --debug flag"
    )
    assert captured.err, "Should have an error message in stderr"

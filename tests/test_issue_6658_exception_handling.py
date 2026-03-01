"""Regression tests for Issue #6658: Broad exception catch may hide unexpected errors.

This test file ensures that:
1. Specific exceptions (ValueError, OSError, json.JSONDecodeError) are caught separately
2. A --debug flag is available to show full tracebacks for debugging
3. User-friendly messages are shown by default, full traceback with --debug
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_has_debug_flag() -> None:
    """The CLI should have a --debug flag for verbose error output."""
    parser = build_parser()
    # Parse with --debug flag
    args = parser.parse_args(["--debug", "list"])
    assert hasattr(args, "debug"), "CLI should have a --debug flag"
    assert args.debug is True, "--debug flag should be True when specified"


def test_cli_debug_shows_traceback_on_error(tmp_path, capsys) -> None:
    """When --debug is enabled, full traceback should be shown on errors."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--debug", "--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # With --debug, traceback should be included in output
    combined_output = captured.err + captured.out
    assert "Traceback" in combined_output, f"--debug should show traceback, got: {combined_output}"


def test_cli_no_debug_hides_traceback_on_error(tmp_path, capsys) -> None:
    """Without --debug, no traceback should be shown to user."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    combined_output = captured.err + captured.out
    # Without --debug, no traceback should be shown
    assert "Traceback" not in combined_output, (
        f"Without --debug, no traceback should be shown, got: {combined_output}"
    )


def test_cli_handles_value_error_specifically(tmp_path, capsys) -> None:
    """ValueError should be caught and handled with user-friendly message."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # Should show user-friendly error message
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_handles_os_error_specifically(tmp_path, capsys) -> None:
    """OSError should be caught and handled with user-friendly message."""
    db = tmp_path / "db.json"
    # Create a directory at the db path to trigger OSError when trying to write
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # Should show user-friendly error message
    combined_output = captured.err + captured.out
    assert len(combined_output) > 0, "Should have error message"


def test_cli_debug_includes_exception_type(tmp_path, capsys) -> None:
    """With --debug, the exception type should be visible in output."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--debug", "--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    combined_output = captured.err + captured.out
    # Should show ValueError in traceback
    assert "ValueError" in combined_output, (
        f"--debug should show exception type, got: {combined_output}"
    )

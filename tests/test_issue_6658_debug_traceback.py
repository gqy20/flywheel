"""Regression tests for Issue #6658: Broad exception catch may hide unexpected errors.

This test file ensures that:
1. Normal CLI usage shows user-friendly error messages (no traceback)
2. With --debug flag, full traceback is logged for debugging
3. Specific exceptions are handled appropriately
"""

from __future__ import annotations

from flywheel.cli import build_parser, main, run_command


def test_cli_debug_flag_exists() -> None:
    """--debug flag should be available in the argument parser."""
    parser = build_parser()
    # Parse with --debug flag
    args = parser.parse_args(["--debug", "list"])
    assert hasattr(args, "debug"), "Parser should have debug attribute"
    assert args.debug is True, "--debug flag should set debug to True"


def test_cli_no_debug_shows_user_friendly_error(tmp_path, capsys) -> None:
    """Without --debug, errors should be user-friendly without traceback."""
    db = tmp_path / "invalid.json"
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 on error"

    captured = capsys.readouterr()
    # Should NOT contain Python traceback
    assert "Traceback (most recent call last)" not in captured.err
    assert "Traceback (most recent call last)" not in captured.out
    # Should contain user-friendly error message
    assert "error" in captured.err.lower() or "error" in captured.out.lower()


def test_cli_debug_shows_traceback_on_error(tmp_path, capsys) -> None:
    """With --debug, errors should include full traceback for debugging."""
    db = tmp_path / "invalid.json"
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--debug", "--db", str(db), "list"])

    result = run_command(args)
    assert result == 1, "run_command should return 1 on error"

    captured = capsys.readouterr()
    # With --debug, should contain traceback in stderr
    combined_output = captured.err + captured.out
    assert "Traceback" in combined_output, (
        f"With --debug, should show traceback. Got stderr: {captured.err!r}, stdout: {captured.out!r}"
    )


def test_cli_debug_main_function_integration(tmp_path, capsys) -> None:
    """Integration test: main() function should support --debug flag."""
    db = tmp_path / "invalid.json"
    db.write_text('{"invalid": json}', encoding="utf-8")

    # Test without debug - should be user-friendly
    result = main(["--db", str(db), "list"])
    assert result == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err

    # Test with debug - should show traceback
    result = main(["--debug", "--db", str(db), "list"])
    assert result == 1
    captured = capsys.readouterr()
    combined = captured.err + captured.out
    assert "Traceback" in combined, (
        f"With --debug, main() should show traceback. Got: {combined!r}"
    )


def test_cli_value_error_still_user_friendly_without_debug(tmp_path, capsys) -> None:
    """ValueError (like 'todo not found') should still be user-friendly."""
    db = tmp_path / "test.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # Should show error message
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()
    # Should NOT show traceback for expected errors
    assert "Traceback" not in captured.err

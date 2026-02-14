"""Regression tests for Issue #3320: Broad Exception catch may hide KeyboardInterrupt and SystemExit.

This test file ensures that run_command does NOT catch KeyboardInterrupt and SystemExit,
which should propagate to allow proper CLI termination.

Security Note: While KeyboardInterrupt and SystemExit inherit from BaseException (not Exception),
using explicit exception types (ValueError, OSError) is a security best practice that:
1. Makes error handling intentions explicit
2. Prevents accidentally catching unintended exceptions if code structure changes
3. Follows the principle of least surprise for maintainers
"""

from __future__ import annotations

import pytest

from flywheel.cli import build_parser, run_command


def test_keyboard_interrupt_propagates(tmp_path) -> None:
    """run_command should NOT catch KeyboardInterrupt.

    KeyboardInterrupt (Ctrl+C) should propagate to allow immediate termination.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    # Direct test: KeyboardInterrupt should propagate, not be caught
    with pytest.raises(KeyboardInterrupt):
        import flywheel.cli as cli_module

        original_add = cli_module.TodoApp.add

        def add_with_interrupt(self, text):
            raise KeyboardInterrupt("User cancelled")

        cli_module.TodoApp.add = add_with_interrupt
        try:
            run_command(args)
        finally:
            cli_module.TodoApp.add = original_add


def test_system_exit_propagates(tmp_path) -> None:
    """run_command should NOT catch SystemExit.

    SystemExit should propagate correctly for proper program termination.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    # Direct test: SystemExit should propagate, not be caught
    with pytest.raises(SystemExit):
        import flywheel.cli as cli_module

        original_add = cli_module.TodoApp.add

        def add_with_exit(self, text):
            raise SystemExit(42)

        cli_module.TodoApp.add = add_with_exit
        try:
            run_command(args)
        finally:
            cli_module.TodoApp.add = original_add


def test_value_error_is_caught(tmp_path, capsys) -> None:
    """run_command should catch ValueError.

    Business logic errors like ValueError should be caught and formatted.
    """
    db = tmp_path / "db.json"

    parser = build_parser()
    # Trigger ValueError by trying to mark non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)

    assert result == 1, "run_command should return 1 on ValueError"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_os_error_is_caught(tmp_path, capsys) -> None:
    """run_command should catch OSError.

    OS-level errors should be caught and formatted.
    """
    db = tmp_path / "db.json"
    # Create a directory at the db path to trigger OSError when trying to write
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)

    assert result == 1, "run_command should return 1 on OSError"
    captured = capsys.readouterr()
    assert captured.err or captured.out, "Error message should be present"


def test_json_decode_error_is_caught(tmp_path, capsys) -> None:
    """run_command should catch json.JSONDecodeError.

    JSON parsing errors should be caught and formatted.
    """
    db = tmp_path / "invalid.json"
    # Write invalid JSON that will cause json.JSONDecodeError
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)

    assert result == 1, "run_command should return 1 on JSON decode error"
    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "error" in captured.out.lower()

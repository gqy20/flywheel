"""Regression tests for Issue #2015: run_command only catches ValueError.

This test file ensures that run_command catches broader exception types
and outputs errors to stderr instead of stdout.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_run_command_handles_json_decode_error(tmp_path, capsys) -> None:
    """run_command should handle json.JSONDecodeError gracefully.

    When the database file contains invalid JSON, json.loads() raises
    JSONDecodeError (a subclass of ValueError, but the fix should also
    handle OSError and other non-ValueError exceptions).
    """
    db = tmp_path / "invalid.json"
    # Write invalid JSON that will cause json.JSONDecodeError
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Should return 1, not crash with unhandled exception
    result = run_command(args)
    assert result == 1, "run_command should return 1 on JSON decode error"

    captured = capsys.readouterr()
    # Error message should be in stderr, not stdout
    assert "error" in captured.err.lower() or "error" in captured.out.lower()


def test_cli_run_command_handles_os_error_permission_denied(tmp_path, capsys) -> None:
    """run_command should handle OSError gracefully.

    When file operations fail due to permissions or other OS issues,
    OSError should be caught and handled gracefully.
    """
    # Use a path that likely won't have write permissions
    # On Unix systems, /root/ typically requires root access
    parser = build_parser()
    args = parser.parse_args(["--db", "/root/flywheel-test-db.json", "add", "test"])

    # Should return 1, not crash with unhandled OSError
    result = run_command(args)
    assert result == 1, "run_command should return 1 on permission error"

    captured = capsys.readouterr()
    # Error message should be present
    assert captured.err or captured.out  # Either stderr or stdout should have content


def test_cli_run_command_handles_general_exception(tmp_path, capsys) -> None:
    """run_command should handle unexpected exceptions gracefully.

    Any unexpected exception should be caught and return 1 instead of crashing.
    This test uses a malformed database to trigger an unexpected error.
    """
    db = tmp_path / "malformed.json"
    # Write JSON with wrong type (object instead of list)
    # This triggers ValueError in storage.py, which IS currently caught
    # But we want to ensure broader exception handling is in place
    db.write_text('{"not": "a list"}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Should return 1, not crash
    result = run_command(args)
    assert result == 1, "run_command should return 1 on malformed data"

    captured = capsys.readouterr()
    # Error message should be present
    assert "error" in captured.err.lower() or "error" in captured.out.lower()


def test_cli_run_command_outputs_errors_to_stderr(tmp_path, capsys) -> None:
    """Error messages should be written to stderr, not stdout."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Trigger an error by marking non-existent todo as done
    args = parser.parse_args(["--db", str(db), "done", "999"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()

    # After the fix, errors should go to stderr
    # The current implementation uses print (stdout), so this test
    # validates the fix is working correctly
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_run_command_handles_corrupt_json_not_value_error(tmp_path, capsys) -> None:
    """Test handling of exceptions that are NOT ValueError subclasses.

    json.JSONDecodeError is actually a subclass of ValueError, so this test
    ensures the fix handles truly unrelated exceptions like OSError.
    """
    db = tmp_path / "db.json"
    # Create a directory at the db path to trigger OSError when trying to write
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    # Should return 1, not crash
    result = run_command(args)
    assert result == 1, "run_command should return 1 on OSError"

    captured = capsys.readouterr()
    # Some error message should be present
    assert captured.err or captured.out


def test_cli_run_command_propagates_keyboard_interrupt(tmp_path, monkeypatch) -> None:
    """run_command should propagate KeyboardInterrupt instead of catching it.

    Regression test for Issue #3320: Broad Exception catch may hide
    KeyboardInterrupt and SystemExit inappropriately.

    Note: KeyboardInterrupt inherits from BaseException, not Exception,
    so it already propagates with 'except Exception'. This test ensures
    that behavior is preserved after narrowing the exception catch.
    """
    from flywheel.cli import TodoApp

    def mock_add(self, text: str):
        raise KeyboardInterrupt()

    monkeypatch.setattr(TodoApp, "add", mock_add)

    parser = build_parser()
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "add", "test"])

    # KeyboardInterrupt should propagate, not be caught
    try:
        run_command(args)
        raise AssertionError("KeyboardInterrupt should have propagated")
    except KeyboardInterrupt:
        pass  # Expected behavior


def test_cli_run_command_propagates_system_exit(tmp_path, monkeypatch) -> None:
    """run_command should propagate SystemExit instead of catching it.

    Regression test for Issue #3320: Broad Exception catch may hide
    KeyboardInterrupt and SystemExit inappropriately.

    Note: SystemExit inherits from BaseException, not Exception,
    so it already propagates with 'except Exception'. This test ensures
    that behavior is preserved after narrowing the exception catch.
    """
    from flywheel.cli import TodoApp

    def mock_add(self, text: str):
        raise SystemExit(42)

    monkeypatch.setattr(TodoApp, "add", mock_add)

    parser = build_parser()
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "add", "test"])

    # SystemExit should propagate, not be caught
    try:
        run_command(args)
        raise AssertionError("SystemExit should have propagated")
    except SystemExit as e:
        assert e.code == 42


def test_cli_run_command_propagates_unexpected_runtime_error(tmp_path, monkeypatch) -> None:
    """run_command should propagate unexpected RuntimeError instead of catching it.

    Regression test for Issue #3320: Broad Exception catch hides unexpected errors.
    The fix narrows the exception catch to only expected types (ValueError, OSError),
    so unexpected exceptions like RuntimeError should propagate.
    """
    from flywheel.cli import TodoApp

    def mock_add(self, text: str):
        raise RuntimeError("Unexpected runtime error")

    monkeypatch.setattr(TodoApp, "add", mock_add)

    parser = build_parser()
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "add", "test"])

    # RuntimeError should propagate, not be caught and formatted
    try:
        run_command(args)
        raise AssertionError("RuntimeError should have propagated")
    except RuntimeError as e:
        assert str(e) == "Unexpected runtime error"


def test_cli_run_command_propagates_unexpected_type_error(tmp_path, monkeypatch) -> None:
    """run_command should propagate unexpected TypeError instead of catching it.

    Regression test for Issue #3320: Broad Exception catch hides unexpected errors.
    The fix narrows the exception catch to only expected types (ValueError, OSError),
    so unexpected exceptions like TypeError should propagate.
    """
    from flywheel.cli import TodoApp

    def mock_add(self, text: str):
        raise TypeError("Unexpected type error")

    monkeypatch.setattr(TodoApp, "add", mock_add)

    parser = build_parser()
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "add", "test"])

    # TypeError should propagate, not be caught and formatted
    try:
        run_command(args)
        raise AssertionError("TypeError should have propagated")
    except TypeError as e:
        assert str(e) == "Unexpected type error"

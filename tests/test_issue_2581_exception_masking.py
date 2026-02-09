"""Regression tests for Issue #2581: Exception handler catches all exceptions indiscriminately.

This test file ensures that run_command only catches specific exception types
(ValueError, OSError, json.JSONDecodeError) and lets programming errors
(AttributeError, TypeError, NameError, etc.) propagate to surface bugs early.
"""

from __future__ import annotations

import pytest

from flywheel.cli import build_parser, run_command


def test_programming_errors_propagate_attribute_error(tmp_path) -> None:
    """Programming errors like AttributeError should NOT be caught.

    This test ensures that bugs in the code (like accessing a non-existent
    attribute) will surface immediately instead of being silently caught
    and returning 1.
    """
    db = tmp_path / "db.json"
    # Create a valid database
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()

    # Monkey-patch the list command to trigger an AttributeError
    # This simulates a programming bug where we access a non-existent attribute
    from flywheel import cli

    original_list = cli.TodoApp.list
    def buggy_list(self, show_all: bool = True):
        # Intentionally access non-existent attribute to simulate a bug
        return self.non_existent_attribute  # type: ignore[attr-defined]

    cli.TodoApp.list = buggy_list

    try:
        args = parser.parse_args(["--db", str(db), "list"])
        # Should raise AttributeError, not return 1
        with pytest.raises(AttributeError, match="non_existent_attribute"):
            run_command(args)
    finally:
        # Restore original method
        cli.TodoApp.list = original_list


def test_programming_errors_propagate_type_error(tmp_path) -> None:
    """Programming errors like TypeError should NOT be caught.

    This test ensures that type errors (e.g., wrong number of arguments)
    will surface immediately instead of being silently caught.
    """
    db = tmp_path / "db.json"
    # Create a valid database
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()

    # Monkey-patch the list command to trigger a TypeError
    from flywheel import cli

    original_list = cli.TodoApp.list
    def buggy_list(self, show_all: bool = True):
        # Intentionally call with wrong type to simulate a bug
        return len(None)  # type: ignore[arg-type]

    cli.TodoApp.list = buggy_list

    try:
        args = parser.parse_args(["--db", str(db), "list"])
        # Should raise TypeError, not return 1
        with pytest.raises(TypeError):
            run_command(args)
    finally:
        # Restore original method
        cli.TodoApp.list = original_list


def test_programming_errors_propagate_name_error(tmp_path) -> None:
    """Programming errors like NameError should NOT be caught.

    This test ensures that undefined variable errors will surface immediately.
    """
    db = tmp_path / "db.json"
    # Create a valid database
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()

    # Monkey-patch the list command to trigger a NameError
    from flywheel import cli

    original_list = cli.TodoApp.list
    def buggy_list(self, show_all: bool = True):
        # Intentionally reference undefined variable
        return undefined_variable  # type: ignore[name-defined]  # noqa: F821

    cli.TodoApp.list = buggy_list

    try:
        args = parser.parse_args(["--db", str(db), "list"])
        # Should raise NameError, not return 1
        with pytest.raises(NameError):
            run_command(args)
    finally:
        # Restore original method
        cli.TodoApp.list = original_list


def test_expected_value_error_is_caught(tmp_path, capsys) -> None:
    """Expected ValueError SHOULD be caught and handled gracefully.

    This test ensures that legitimate errors (like invalid todo ID)
    are still caught and result in a user-friendly error message.
    """
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    # Should return 1 with error message
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "error" in captured.err.lower()


def test_expected_os_error_is_caught(tmp_path, capsys) -> None:
    """Expected OSError SHOULD be caught and handled gracefully.

    This test ensures that file system errors (like permission denied)
    are caught and result in a user-friendly error message.
    """
    parser = build_parser()
    # Try to write to a location that likely requires root access
    args = parser.parse_args(["--db", "/root/flywheel-test-db.json", "add", "test"])

    # Should return 1 with error message
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    # Error message should be present
    assert captured.err or captured.out


def test_expected_json_decode_error_is_caught(tmp_path, capsys) -> None:
    """Expected json.JSONDecodeError SHOULD be caught and handled gracefully.

    This test ensures that invalid JSON files are handled gracefully.
    """
    db = tmp_path / "invalid.json"
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    # Should return 1 with error message
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "error" in captured.out.lower()


def test_key_error_should_propagate_as_programming_error(tmp_path) -> None:
    """KeyError (programming error) should NOT be caught.

    KeyError typically indicates a bug in the code (accessing a missing
    dictionary key) and should propagate to surface the issue early.
    """
    db = tmp_path / "db.json"
    db.write_text("[]", encoding="utf-8")

    parser = build_parser()

    # Monkey-patch to trigger a KeyError
    from flywheel import cli

    original_list = cli.TodoApp.list
    def buggy_list(self, show_all: bool = True):
        # Intentionally access missing dictionary key
        return {}["missing_key"]

    cli.TodoApp.list = buggy_list

    try:
        args = parser.parse_args(["--db", str(db), "list"])
        # Should raise KeyError, not return 1
        with pytest.raises(KeyError):
            run_command(args)
    finally:
        # Restore original method
        cli.TodoApp.list = original_list

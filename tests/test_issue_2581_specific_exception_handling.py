"""Regression tests for Issue #2581: run_command should only catch specific exceptions.

This test file ensures that run_command does NOT catch programming errors
like AttributeError, TypeError, etc. These should propagate and crash
so that bugs are surfaced early during development.
"""

from __future__ import annotations

import pytest

from flywheel.cli import build_parser, run_command


def test_cli_run_type_error_on_iteration_propagates(tmp_path) -> None:
    """Programming errors like TypeError (NoneType not iterable) should propagate."""
    db = tmp_path / "db.json"
    db.write_text('[]', encoding="utf-8")

    parser = build_parser()
    # Use --pending flag which causes list to iterate over todos
    args = parser.parse_args(["--db", str(db), "list", "--pending"])

    from flywheel.cli import TodoApp

    original_load = TodoApp._load

    def buggy_load(self):
        # Simulate a programming bug: return None instead of list
        # This will cause TypeError when trying to iterate
        return None

    try:
        # Patch and test
        TodoApp._load = buggy_load

        # This should raise TypeError, not return 1
        with pytest.raises(TypeError):
            run_command(args)
    finally:
        # Restore original
        TodoApp._load = original_load


def test_cli_run_type_error_direct_propagates(tmp_path) -> None:
    """Programming errors like TypeError should propagate, NOT be caught."""
    db = tmp_path / "db.json"
    db.write_text('[]', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test todo"])

    from flywheel.cli import TodoApp

    original_add = TodoApp.add

    def buggy_add(self, text):
        # Simulate a programming bug: trying to add string and int
        # This will cause TypeError when text is used in concatenation
        raise TypeError("can only concatenate str (not 'int') to str")

    try:
        TodoApp.add = buggy_add

        # This should raise TypeError, not return 1
        with pytest.raises(TypeError):
            run_command(args)
    finally:
        # Restore original
        TodoApp.add = original_add


def test_cli_run_attribute_error_propagates(tmp_path) -> None:
    """Programming errors like AttributeError should propagate, NOT be caught.

    This is the KEY test for issue #2581. If run_command catches
    AttributeError and returns 1, this test will fail because the
    exception won't propagate to pytest.
    """
    db = tmp_path / "db.json"
    db.write_text('[]', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    from flywheel.cli import TodoApp

    original_add = TodoApp.add

    def buggy_add(self, text):
        # Simulate a programming bug: accessing non-existent attribute
        # This will cause AttributeError
        return self.nonexistent_attribute

    try:
        TodoApp.add = buggy_add

        # This should raise AttributeError, not return 1
        with pytest.raises(AttributeError):
            run_command(args)
    finally:
        # Restore original
        TodoApp.add = original_add


def test_cli_value_error_is_caught(tmp_path, capsys) -> None:
    """Expected ValueError should be caught and return 1.

    This ensures the fix doesn't break legitimate error handling.
    """
    db = tmp_path / "db.json"
    db.write_text('[]', encoding="utf-8")

    parser = build_parser()
    # Try to mark a non-existent todo as done - this raises ValueError
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1, "ValueError should be caught and return 1"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_os_error_is_caught(tmp_path, capsys) -> None:
    """Expected OSError should be caught and return 1.

    This ensures the fix doesn't break legitimate error handling.
    """
    db = tmp_path / "db.json"
    # Create a directory at the db path to trigger OSError
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)
    assert result == 1, "OSError should be caught and return 1"

    captured = capsys.readouterr()
    # Some error message should be present
    assert captured.err or captured.out


def test_cli_json_decode_error_is_caught(tmp_path, capsys) -> None:
    """Expected json.JSONDecodeError should be caught and return 1.

    This ensures the fix doesn't break legitimate error handling.
    """
    db = tmp_path / "db.json"
    # Write invalid JSON
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)
    assert result == 1, "json.JSONDecodeError should be caught and return 1"

    captured = capsys.readouterr()
    # Error message should be present
    assert "error" in captured.err.lower() or "error" in captured.out.lower()


def test_cli_name_error_propagates(tmp_path) -> None:
    """Programming errors like NameError should propagate, NOT be caught."""
    db = tmp_path / "db.json"
    db.write_text('[]', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    from flywheel.cli import TodoApp

    original_list = TodoApp.list

    def buggy_list(self, show_all=True):
        # Simulate a programming bug: undefined variable
        return undefined_variable  # noqa: F821

    try:
        TodoApp.list = buggy_list

        # This should raise NameError, not return 1
        with pytest.raises(NameError):
            run_command(args)
    finally:
        # Restore original
        TodoApp.list = original_list

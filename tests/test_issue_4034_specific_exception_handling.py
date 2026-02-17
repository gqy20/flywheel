"""Regression tests for Issue #4034: run_command catches specific exceptions only.

The issue is that run_command catches all Exception types, which masks program bugs
like AttributeError, TypeError. The fix should catch only specific expected exceptions
(ValueError, OSError, json.JSONDecodeError) and let unexpected exceptions propagate
for debugging.
"""

from __future__ import annotations

import json
from unittest import mock

from flywheel.cli import build_parser, run_command


def test_cli_catches_value_error_for_invalid_id(tmp_path, capsys) -> None:
    """ValueError (e.g., todo not found) should be caught and return 1."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "done", "999"])

    result = run_command(args)
    assert result == 1, "ValueError should result in exit code 1"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()


def test_cli_catches_os_error_for_permission_denied(tmp_path, capsys) -> None:
    """OSError (e.g., permission denied) should be caught and return 1."""
    # Create a directory at the db path to trigger OSError when trying to write
    db = tmp_path / "db.json"
    db.mkdir()

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "test"])

    result = run_command(args)
    assert result == 1, "OSError should result in exit code 1"

    captured = capsys.readouterr()
    assert captured.err  # Some error message should be present


def test_cli_catches_json_decode_error(tmp_path, capsys) -> None:
    """json.JSONDecodeError should be caught and return 1.

    Note: json.JSONDecodeError is actually wrapped by storage.py into ValueError,
    but we test that it's handled properly through the exception chain.
    """
    db = tmp_path / "invalid.json"
    # Write invalid JSON
    db.write_text('{"invalid": json}', encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "list"])

    result = run_command(args)
    assert result == 1, "JSON decode errors should result in exit code 1"

    captured = capsys.readouterr()
    assert captured.err  # Some error message should be present


def test_cli_propagates_attribute_error(tmp_path) -> None:
    """AttributeError (program bug) should propagate, not be caught.

    This is the key test for issue #4034: unexpected exceptions like
    AttributeError should NOT be caught - they should propagate to expose bugs.
    """
    parser = build_parser()
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "list"])

    # Mock the TodoApp to raise AttributeError (simulating a program bug)
    with mock.patch("flywheel.cli.TodoApp") as mock_app:
        mock_app_instance = mock.Mock()
        mock_app_instance.list.side_effect = AttributeError("simulated bug")
        mock_app.return_value = mock_app_instance

        # AttributeError should propagate (not be caught)
        try:
            run_command(args)
            assert False, "AttributeError should have propagated"
        except AttributeError as e:
            assert "simulated bug" in str(e)


def test_cli_propagates_type_error(tmp_path) -> None:
    """TypeError (program bug) should propagate, not be caught.

    This is another key test for issue #4034: unexpected exceptions like
    TypeError should NOT be caught - they should propagate to expose bugs.
    """
    parser = build_parser()
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "list"])

    # Mock the TodoApp to raise TypeError (simulating a program bug)
    with mock.patch("flywheel.cli.TodoApp") as mock_app:
        mock_app_instance = mock.Mock()
        mock_app_instance.list.side_effect = TypeError("simulated bug")
        mock_app.return_value = mock_app_instance

        # TypeError should propagate (not be caught)
        try:
            run_command(args)
            assert False, "TypeError should have propagated"
        except TypeError as e:
            assert "simulated bug" in str(e)


def test_cli_propagates_key_error(tmp_path) -> None:
    """KeyError (program bug) should propagate, not be caught."""
    parser = build_parser()
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "list"])

    # Mock the TodoApp to raise KeyError (simulating a program bug)
    with mock.patch("flywheel.cli.TodoApp") as mock_app:
        mock_app_instance = mock.Mock()
        mock_app_instance.list.side_effect = KeyError("simulated bug")
        mock_app.return_value = mock_app_instance

        # KeyError should propagate (not be caught)
        try:
            run_command(args)
            assert False, "KeyError should have propagated"
        except KeyError as e:
            assert "simulated bug" in str(e)


def test_cli_catches_value_error_for_empty_todo_text(tmp_path, capsys) -> None:
    """ValueError for empty todo text should be caught and return 1."""
    db = tmp_path / "db.json"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "add", "   "])  # Whitespace only

    result = run_command(args)
    assert result == 1, "ValueError should result in exit code 1"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower()

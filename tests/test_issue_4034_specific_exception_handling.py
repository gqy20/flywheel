"""Regression tests for Issue #4034: run_command should catch specific exceptions.

This test file ensures that run_command catches only expected exception types
(ValueError, OSError, json.JSONDecodeError) and lets program bugs
(AttributeError, TypeError) propagate for debugging.
"""

from __future__ import annotations

from unittest import mock

import pytest

from flywheel.cli import TodoApp, build_parser, run_command


class TestExpectedExceptionsCaught:
    """Tests for exceptions that SHOULD be caught and return exit code 1."""

    def test_value_error_returns_exit_code_1(self, tmp_path, capsys) -> None:
        """ValueError (user input issues) should be caught and return 1."""
        db = tmp_path / "db.json"
        parser = build_parser()
        # Trigger ValueError by marking non-existent todo as done
        args = parser.parse_args(["--db", str(db), "done", "999"])

        result = run_command(args)
        assert result == 1, "ValueError should return exit code 1"

        captured = capsys.readouterr()
        assert "error" in captured.err.lower() or "not found" in captured.err.lower()

    def test_os_error_returns_exit_code_1(self, tmp_path, capsys) -> None:
        """OSError (file permission issues) should be caught and return 1."""
        db = tmp_path / "db.json"
        # Create a directory at the db path to trigger OSError when trying to write
        db.mkdir()

        parser = build_parser()
        args = parser.parse_args(["--db", str(db), "add", "test"])

        result = run_command(args)
        assert result == 1, "OSError should return exit code 1"

        captured = capsys.readouterr()
        assert captured.err or captured.out

    def test_json_decode_error_returns_exit_code_1(self, tmp_path, capsys) -> None:
        """json.JSONDecodeError should be caught and return 1."""
        db = tmp_path / "invalid.json"
        # Write invalid JSON that will cause json.JSONDecodeError
        db.write_text('{"invalid": json}', encoding="utf-8")

        parser = build_parser()
        args = parser.parse_args(["--db", str(db), "list"])

        result = run_command(args)
        assert result == 1, "json.JSONDecodeError should return exit code 1"

        captured = capsys.readouterr()
        assert "error" in captured.err.lower() or "error" in captured.out.lower()


class TestUnexpectedExceptionsPropagate:
    """Tests for exceptions that should NOT be caught (program bugs)."""

    def test_attribute_error_propagates(self, tmp_path) -> None:
        """AttributeError (program bug) should NOT be caught and should propagate."""
        db = tmp_path / "db.json"
        parser = build_parser()
        args = parser.parse_args(["--db", str(db), "list"])

        # Mock TodoApp.__init__ to return an app with a broken storage
        # that raises AttributeError when load() is called (simulating a program bug)
        def broken_init(self, db_path=None):
            self.storage = None  # Deliberately set to None to cause AttributeError

        # This should raise AttributeError when app.list() calls self.storage.load()
        # because self.storage is None and None has no attribute 'load'
        with (
            mock.patch.object(TodoApp, "__init__", broken_init),
            pytest.raises(AttributeError),
        ):
            run_command(args)

    def test_type_error_propagates(self, tmp_path) -> None:
        """TypeError (program bug) should NOT be caught and should propagate."""
        db = tmp_path / "db.json"
        db.write_text("[]", encoding="utf-8")  # Valid empty DB

        parser = build_parser()
        args = parser.parse_args(["--db", str(db), "list"])

        # Mock the list method to raise TypeError (simulating a program bug)
        # This should raise TypeError, not return 1
        with (
            mock.patch.object(TodoApp, "list", side_effect=TypeError("program bug")),
            pytest.raises(TypeError),
        ):
            run_command(args)

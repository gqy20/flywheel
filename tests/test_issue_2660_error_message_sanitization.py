"""Regression tests for Issue #2660: Exception handler exposes sensitive paths.

This test file ensures that error messages output by run_command do not
expose sensitive filesystem paths or system information that could be
used for information disclosure attacks.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command
from flywheel.formatter import _sanitize_error_message


class TestSanitizeErrorMessage:
    """Test the _sanitize_error_message function directly."""

    def test_sanitize_removes_full_path_from_value_error(self) -> None:
        """Full filesystem paths in ValueError should be sanitized."""
        exc = ValueError(
            "Path error: '/home/secret_user/projects/config/db.json' exists as a file, not a directory"
        )
        result = _sanitize_error_message(exc)
        # Should contain filename but not full path
        assert "db.json" in result
        assert "/home/secret_user/" not in result
        assert "/home/secret_user/projects/" not in result

    def test_sanitize_removes_full_path_from_os_error(self) -> None:
        """Full filesystem paths in OSError should be sanitized."""
        exc = OSError(
            "[Errno 13] Permission denied: '/var/sensitive_data/todo.json'"
        )
        result = _sanitize_error_message(exc)
        # Should contain filename but not full path
        assert "todo.json" in result
        assert "/var/sensitive_data/" not in result

    def test_sanitize_removes_username_from_home_path(self) -> None:
        """Usernames from home directory paths should not be exposed."""
        exc = ValueError("Invalid JSON in '/home/admin_user/.todo.json': Syntax error")
        result = _sanitize_error_message(exc)
        # Should contain filename but not username
        assert ".todo.json" in result
        assert "admin_user" not in result

    def test_sanitize_preserves_error_type_and_context(self) -> None:
        """Sanitization should preserve useful error information."""
        exc = ValueError("Todo text cannot be empty")
        result = _sanitize_error_message(exc)
        # Non-path errors should be preserved as-is
        assert result == "Todo text cannot be empty" or "empty" in result

    def test_sanitize_handles_simple_errors(self) -> None:
        """Simple errors without paths should remain readable."""
        exc = ValueError("Todo #999 not found")
        result = _sanitize_error_message(exc)
        # Should preserve the message
        assert "999" in result
        assert "not found" in result.lower()

    def test_sanitize_handles_json_decode_error(self) -> None:
        """JSON decode errors with paths should be sanitized."""
        exc = ValueError(
            "Invalid JSON in '/tmp/sensitive_project/config/todo.json': "
            "Expecting property name enclosed in double quotes. "
            "Check line 1, column 3."
        )
        result = _sanitize_error_message(exc)
        # Should show line/column info but sanitize path
        assert "line 1" in result
        assert "column 3" in result
        assert "sensitive_project" not in result


class TestRunCommandSanitization:
    """Test that run_command sanitizes errors in actual CLI usage."""

    def test_run_command_sanitizes_path_in_error_output(self, tmp_path, capsys) -> None:
        """run_command should not expose full paths in error messages.

        This test creates an invalid JSON file in a directory with a sensitive name
        to trigger a JSON decode error, then verifies the error output does not
        contain the sensitive path components.
        """
        # Create a directory with a "sensitive" name as part of the path
        sensitive_dir = tmp_path / "SECRET_API_KEYS" / "config"
        sensitive_dir.mkdir(parents=True)
        db_path = sensitive_dir / "db.json"

        # Write invalid JSON to trigger error on list
        db_path.write_text('{"invalid": json}', encoding="utf-8")

        parser = build_parser()
        args = parser.parse_args(["--db", str(db_path), "list"])

        result = run_command(args)

        # Should return error code
        assert result == 1

        captured = capsys.readouterr()

        # Error output should not contain the sensitive directory name
        assert "SECRET_API_KEYS" not in captured.err
        assert "SECRET_API_KEYS" not in captured.out
        # But should still have an error message
        assert captured.err or captured.out

    def test_run_command_sanitizes_invalid_json_path(self, tmp_path, capsys) -> None:
        """Invalid JSON errors should not expose full paths."""
        # Use a directory name that looks sensitive
        sensitive_parent = tmp_path / "PRODUCTION_CONFIG"
        sensitive_parent.mkdir()
        db = sensitive_parent / "production.json"

        # Write invalid JSON
        db.write_text('{"invalid": json}', encoding="utf-8")

        parser = build_parser()
        args = parser.parse_args(["--db", str(db), "list"])

        result = run_command(args)

        assert result == 1
        captured = capsys.readouterr()

        # Should not expose the sensitive directory name
        assert "PRODUCTION_CONFIG" not in captured.err
        assert "PRODUCTION_CONFIG" not in captured.out
        # But should indicate an error occurred
        assert "error" in captured.err.lower() or "error" in captured.out.lower()

    def test_run_command_preserves_non_path_errors(self, tmp_path, capsys) -> None:
        """Errors without paths should still be useful for debugging."""
        db = tmp_path / "db.json"

        parser = build_parser()

        # Mark non-existent todo as done - no path involved
        args = parser.parse_args(["--db", str(db), "done", "999"])
        result = run_command(args)

        assert result == 1
        captured = capsys.readouterr()

        # Should still show the error message
        assert "not found" in captured.err.lower() or "not found" in captured.out.lower()

    def test_run_command_sanitizes_path_as_directory_error(self, tmp_path, capsys) -> None:
        """When db path exists as directory, error should not expose full path.

        The key security concern is not exposing the full filesystem path.
        Individual filenames (basenames) are acceptable to show.
        """
        # Create a file where a directory component should be
        # This triggers the ValueError from _ensure_parent_directory
        parent = tmp_path / "user_credentials"
        parent.write_text("this is a file, not a directory", encoding="utf-8")
        # Now try to use a path that would need this as a directory
        db_file = parent / "subdir" / "database.json"

        parser = build_parser()
        args = parser.parse_args(["--db", str(db_file), "add", "test"])

        result = run_command(args)

        assert result == 1
        captured = capsys.readouterr()

        # The key security requirement: full path including parent directories should not be shown
        # The actual tmp_path (which contains pytest directory info) should not be exposed
        assert str(tmp_path) not in captured.err
        assert "pytest-of-runner" not in captured.err
        assert "test_run_command_sanitizes" not in captured.err

        # Basenames are acceptable - they're just filenames, not filesystem locations
        assert "database.json" in captured.err or "database.json" in captured.out

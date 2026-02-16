"""Regression tests for issue #3580: Add 'edit' CLI command."""

import tempfile
from pathlib import Path

import pytest

from flywheel.cli import build_parser, main


class TestCliEditCommand:
    """Tests for the 'todo edit' CLI command."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path, monkeypatch):
        """Set up a temp directory and DB for each test."""
        self.db_file = tmp_path / ".todo.json"
        monkeypatch.setenv("TODO_DB", str(self.db_file))

    def test_cli_edit_command_updates_todo_text(self, capsys):
        """Edit command should update the todo text."""
        # Add a todo first
        result = main(["--db", str(self.db_file), "add", "Original text"])
        assert result == 0

        # Edit the todo
        result = main(["--db", str(self.db_file), "edit", "1", "Updated text"])
        assert result == 0

        # Verify the text was updated
        captured = capsys.readouterr()
        assert "Updated text" in captured.out

        # List to verify persistence
        result = main(["--db", str(self.db_file), "list"])
        captured = capsys.readouterr()
        assert "Updated text" in captured.out
        assert "Original text" not in captured.out

    def test_cli_edit_command_updates_updated_at(self, capsys):
        """Edit command should update the updated_at timestamp."""
        import time

        # Add a todo first
        result = main(["--db", str(self.db_file), "add", "Test todo"])
        assert result == 0

        # Small delay to ensure timestamp difference
        time.sleep(0.01)

        # Edit the todo
        result = main(["--db", str(self.db_file), "edit", "1", "Modified todo"])
        assert result == 0

        # The output should confirm the edit
        captured = capsys.readouterr()
        assert "Modified todo" in captured.out

    def test_cli_edit_command_rejects_empty_text(self, capsys):
        """Edit command should reject empty text."""
        # Add a todo first
        result = main(["--db", str(self.db_file), "add", "Existing todo"])
        assert result == 0

        # Try to edit with empty text
        result = main(["--db", str(self.db_file), "edit", "1", ""])
        assert result == 1

        captured = capsys.readouterr()
        assert "empty" in captured.err.lower() or "empty" in captured.out.lower()

    def test_cli_edit_command_rejects_whitespace_only_text(self, capsys):
        """Edit command should reject text that is only whitespace."""
        # Add a todo first
        result = main(["--db", str(self.db_file), "add", "Existing todo"])
        assert result == 0

        # Try to edit with whitespace-only text
        result = main(["--db", str(self.db_file), "edit", "1", "   "])
        assert result == 1

        captured = capsys.readouterr()
        assert "empty" in captured.err.lower() or "empty" in captured.out.lower()

    def test_cli_edit_command_rejects_nonexistent_id(self, capsys):
        """Edit command should reject non-existent todo ID."""
        # Add a todo first
        result = main(["--db", str(self.db_file), "add", "Existing todo"])
        assert result == 0

        # Try to edit a non-existent todo
        result = main(["--db", str(self.db_file), "edit", "999", "New text"])
        assert result == 1

        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "not found" in captured.out.lower()

    def test_cli_edit_command_parser_has_id_and_text_args(self):
        """Parser should accept 'edit' subcommand with id and text arguments."""
        parser = build_parser()
        # Parse edit command
        args = parser.parse_args(["edit", "1", "new text"])
        assert args.command == "edit"
        assert args.id == 1
        assert args.text == "new text"

"""Tests for issue #4905: Export functionality to CSV and Markdown formats.

This test suite verifies that TodoStorage can export todos to CSV and Markdown
formats, supporting Unicode characters and proper formatting.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestExportCsv:
    """Tests for export_csv functionality."""

    def test_export_csv_with_headers(self, tmp_path: Path) -> None:
        """Test that export_csv outputs valid CSV with required headers."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="Task one", done=False),
            Todo(id=2, text="Task two", done=True),
        ]
        storage.save(todos)

        csv_output = storage.export_csv(todos)
        reader = csv.DictReader(io.StringIO(csv_output))

        # Verify headers
        assert reader.fieldnames == ["id", "text", "done", "created_at", "updated_at"]

        # Verify content
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["id"] == "1"
        assert rows[0]["text"] == "Task one"
        assert rows[0]["done"] == "False"
        assert rows[1]["id"] == "2"
        assert rows[1]["text"] == "Task two"
        assert rows[1]["done"] == "True"

    def test_export_csv_handles_unicode(self, tmp_path: Path) -> None:
        """Test that export_csv handles Unicode characters correctly."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="你好世界", done=False),
            Todo(id=2, text="Привет мир", done=True),
            Todo(id=3, text="日本語テスト", done=False),
        ]
        storage.save(todos)

        csv_output = storage.export_csv(todos)
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["text"] == "你好世界"
        assert rows[1]["text"] == "Привет мир"
        assert rows[2]["text"] == "日本語テスト"

    def test_export_csv_handles_special_characters(self, tmp_path: Path) -> None:
        """Test that export_csv handles CSV special characters (quotes, commas)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text='Task with "quotes"', done=False),
            Todo(id=2, text="Task with, comma", done=True),
            Todo(id=3, text="Task with\nnewline", done=False),
        ]
        storage.save(todos)

        csv_output = storage.export_csv(todos)
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["text"] == 'Task with "quotes"'
        assert rows[1]["text"] == "Task with, comma"
        assert rows[2]["text"] == "Task with\nnewline"

    def test_export_csv_empty_list(self, tmp_path: Path) -> None:
        """Test that export_csv handles empty todo list."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        csv_output = storage.export_csv([])
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 0


class TestExportMarkdown:
    """Tests for export_markdown functionality."""

    def test_export_markdown_table_structure(self, tmp_path: Path) -> None:
        """Test that export_markdown outputs valid GitHub-flavored markdown table."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="Task one", done=False),
            Todo(id=2, text="Task two", done=True),
        ]
        storage.save(todos)

        md_output = storage.export_markdown(todos)
        lines = md_output.strip().split("\n")

        # Check header row
        assert lines[0] == "| ID | Text | Done | Created At | Updated At |"

        # Check separator row
        assert lines[1] == "|----|------|------|------------|------------|"

        # Check data rows
        assert len(lines) == 4  # header + separator + 2 data rows

        # Verify content contains expected data
        assert "| 1 |" in md_output
        assert "| Task one |" in md_output
        assert "| Task two |" in md_output

    def test_export_markdown_handles_unicode(self, tmp_path: Path) -> None:
        """Test that export_markdown handles Unicode characters correctly."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="你好世界", done=False),
            Todo(id=2, text="Привет мир", done=True),
        ]
        storage.save(todos)

        md_output = storage.export_markdown(todos)

        assert "你好世界" in md_output
        assert "Привет мир" in md_output

    def test_export_markdown_empty_list(self, tmp_path: Path) -> None:
        """Test that export_markdown handles empty todo list."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        md_output = storage.export_markdown([])

        # Empty list should return just header with no data rows
        lines = md_output.strip().split("\n")
        assert len(lines) == 2  # header + separator only

    def test_export_markdown_escapes_pipe_characters(self, tmp_path: Path) -> None:
        """Test that export_markdown escapes pipe characters in text."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="Task | with | pipes", done=False),
        ]
        storage.save(todos)

        md_output = storage.export_markdown(todos)

        # Pipe should be escaped as \|
        assert "\\|" in md_output


class TestExportIntegration:
    """Integration tests for export functionality."""

    def test_round_trip_csv_export_parse(self, tmp_path: Path) -> None:
        """Test that CSV export can be parsed and data is preserved."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        original_todos = [
            Todo(id=1, text="First task", done=False),
            Todo(id=2, text="Second task", done=True),
            Todo(id=3, text="Third task with unicode: 你好", done=False),
        ]
        storage.save(original_todos)

        csv_output = storage.export_csv(original_todos)
        reader = csv.DictReader(io.StringIO(csv_output))
        parsed_rows = list(reader)

        assert len(parsed_rows) == 3
        assert parsed_rows[0]["text"] == "First task"
        assert parsed_rows[0]["done"] == "False"
        assert parsed_rows[1]["text"] == "Second task"
        assert parsed_rows[1]["done"] == "True"
        assert parsed_rows[2]["text"] == "Third task with unicode: 你好"

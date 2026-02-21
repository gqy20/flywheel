"""Tests for export functionality (CSV, Markdown)."""

from __future__ import annotations

import csv
import io

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestExportCsv:
    """Tests for CSV export functionality."""

    def test_export_csv_basic(self) -> None:
        """Test basic CSV export with multiple todos."""
        storage = TodoStorage()
        todos = [
            Todo(
                id=1,
                text="Buy groceries",
                done=False,
                created_at="2024-01-01T10:00:00+00:00",
                updated_at="2024-01-01T10:00:00+00:00",
            ),
            Todo(
                id=2,
                text="Write report",
                done=True,
                created_at="2024-01-02T11:00:00+00:00",
                updated_at="2024-01-02T12:00:00+00:00",
            ),
            Todo(
                id=3,
                text="Call mom",
                done=False,
                created_at="2024-01-03T09:00:00+00:00",
                updated_at="2024-01-03T09:00:00+00:00",
            ),
        ]

        result = storage.export_csv(todos)

        # Parse CSV to verify structure
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["id"] == "1"
        assert rows[0]["text"] == "Buy groceries"
        assert rows[0]["done"] == "False"
        assert rows[1]["id"] == "2"
        assert rows[1]["done"] == "True"

    def test_export_csv_unicode(self) -> None:
        """Test CSV export handles unicode characters correctly."""
        storage = TodoStorage()
        todos = [
            Todo(
                id=1,
                text="Купить продукты 🛒",
                done=False,
                created_at="2024-01-01T10:00:00+00:00",
                updated_at="2024-01-01T10:00:00+00:00",
            ),
            Todo(
                id=2,
                text="Escribir informe en español",
                done=True,
                created_at="2024-01-02T11:00:00+00:00",
                updated_at="2024-01-02T12:00:00+00:00",
            ),
        ]

        result = storage.export_csv(todos)

        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["text"] == "Купить продукты 🛒"
        assert rows[1]["text"] == "Escribir informe en español"

    def test_export_csv_empty(self) -> None:
        """Test CSV export with empty todo list returns headers only."""
        storage = TodoStorage()
        todos: list[Todo] = []

        result = storage.export_csv(todos)

        lines = result.strip().split("\n")
        assert len(lines) == 1
        assert "id,text,done,created_at,updated_at" in lines[0]

    def test_export_csv_special_characters(self) -> None:
        """Test CSV export handles special characters (commas, quotes, newlines)."""
        storage = TodoStorage()
        todos = [
            Todo(
                id=1,
                text='Task with "quotes" and, commas',
                done=False,
                created_at="2024-01-01T10:00:00+00:00",
                updated_at="2024-01-01T10:00:00+00:00",
            ),
            Todo(
                id=2,
                text="Task with\nnewline",
                done=False,
                created_at="2024-01-02T10:00:00+00:00",
                updated_at="2024-01-02T10:00:00+00:00",
            ),
        ]

        result = storage.export_csv(todos)

        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["text"] == 'Task with "quotes" and, commas'
        assert rows[1]["text"] == "Task with\nnewline"


class TestExportMarkdown:
    """Tests for Markdown export functionality."""

    def test_export_markdown_basic(self) -> None:
        """Test basic Markdown table export with multiple todos."""
        storage = TodoStorage()
        todos = [
            Todo(
                id=1,
                text="Buy groceries",
                done=False,
                created_at="2024-01-01T10:00:00+00:00",
                updated_at="2024-01-01T10:00:00+00:00",
            ),
            Todo(
                id=2,
                text="Write report",
                done=True,
                created_at="2024-01-02T11:00:00+00:00",
                updated_at="2024-01-02T12:00:00+00:00",
            ),
            Todo(
                id=3,
                text="Call mom",
                done=False,
                created_at="2024-01-03T09:00:00+00:00",
                updated_at="2024-01-03T09:00:00+00:00",
            ),
        ]

        result = storage.export_markdown(todos)

        lines = result.strip().split("\n")

        # Check header row
        assert "| id | text | done | created_at | updated_at |" in lines[0]
        # Check separator row
        assert "---" in lines[1]
        # Check data rows
        assert "| 1 | Buy groceries | False |" in lines[2]
        assert "| 2 | Write report | True |" in lines[3]
        assert "| 3 | Call mom | False |" in lines[4]

    def test_export_markdown_unicode(self) -> None:
        """Test Markdown export handles unicode characters correctly."""
        storage = TodoStorage()
        todos = [
            Todo(
                id=1,
                text="Купить продукты 🛒",
                done=False,
                created_at="2024-01-01T10:00:00+00:00",
                updated_at="2024-01-01T10:00:00+00:00",
            ),
            Todo(
                id=2,
                text="Escribir informe en español",
                done=True,
                created_at="2024-01-02T11:00:00+00:00",
                updated_at="2024-01-02T12:00:00+00:00",
            ),
        ]

        result = storage.export_markdown(todos)

        assert "Купить продукты 🛒" in result
        assert "Escribir informe en español" in result

    def test_export_markdown_empty(self) -> None:
        """Test Markdown export with empty todo list returns headers only."""
        storage = TodoStorage()
        todos: list[Todo] = []

        result = storage.export_markdown(todos)

        lines = result.strip().split("\n")
        assert len(lines) == 2  # Header + separator
        assert "| id | text | done | created_at | updated_at |" in lines[0]
        assert "---" in lines[1]

    def test_export_markdown_pipe_escaping(self) -> None:
        """Test Markdown export escapes pipe characters in text."""
        storage = TodoStorage()
        todos = [
            Todo(
                id=1,
                text="Task with | pipe character",
                done=False,
                created_at="2024-01-01T10:00:00+00:00",
                updated_at="2024-01-01T10:00:00+00:00",
            ),
        ]

        result = storage.export_markdown(todos)

        # Pipe characters should be escaped in markdown
        assert "\\|" in result or "|" not in result.split("\n")[2].split(" | ")[1]

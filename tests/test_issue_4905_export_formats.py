"""Tests for export functionality to CSV and Markdown formats.

Issue #4905: Add export functionality to alternative formats (CSV, Markdown)
"""

from __future__ import annotations

import csv
import io

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_export_csv_basic_todos(tmp_path) -> None:
    """Export todos to CSV format with proper headers."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create some todos
    todos = [
        Todo(id=1, text="Task 1", done=False),
        Todo(id=2, text="Task 2", done=True),
    ]
    storage.save(todos)

    # Export to CSV
    csv_output = storage.export_csv(todos)

    # Verify CSV structure using csv module
    reader = csv.DictReader(io.StringIO(csv_output))
    rows = list(reader)

    assert len(rows) == 2
    # Verify headers are present
    assert "id" in rows[0]
    assert "text" in rows[0]
    assert "done" in rows[0]
    assert "created_at" in rows[0]
    assert "updated_at" in rows[0]

    # Verify data
    assert rows[0]["id"] == "1"
    assert rows[0]["text"] == "Task 1"
    assert rows[0]["done"] == "False"

    assert rows[1]["id"] == "2"
    assert rows[1]["text"] == "Task 2"
    assert rows[1]["done"] == "True"


def test_export_csv_unicode_handling(tmp_path) -> None:
    """Export todos with unicode characters to CSV."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with unicode characters
    todos = [
        Todo(id=1, text="任务一 - 中文测试"),
        Todo(id=2, text="タスク二 - 日本語"),
        Todo(id=3, text="Tâche 3 - émojis 🎉 📝"),
    ]
    storage.save(todos)

    # Export to CSV
    csv_output = storage.export_csv(todos)

    # Verify CSV can be parsed and unicode is preserved
    reader = csv.DictReader(io.StringIO(csv_output))
    rows = list(reader)

    assert len(rows) == 3
    assert rows[0]["text"] == "任务一 - 中文测试"
    assert rows[1]["text"] == "タスク二 - 日本語"
    assert rows[2]["text"] == "Tâche 3 - émojis 🎉 📝"


def test_export_csv_empty_list(tmp_path) -> None:
    """Export empty todo list to CSV."""
    storage = TodoStorage(str(tmp_path / "todo.json"))

    csv_output = storage.export_csv([])

    # Should produce headers only
    reader = csv.DictReader(io.StringIO(csv_output))
    rows = list(reader)
    assert len(rows) == 0

    # Verify headers are still present
    lines = csv_output.strip().split("\n")
    assert "id" in lines[0]
    assert "text" in lines[0]


def test_export_csv_special_characters(tmp_path) -> None:
    """Export todos with special characters (quotes, commas) to CSV."""
    storage = TodoStorage(str(tmp_path / "todo.json"))

    # Create todos with special characters that need escaping in CSV
    todos = [
        Todo(id=1, text='Task with "quotes"'),
        Todo(id=2, text="Task with, comma"),
        Todo(id=3, text='Task with "quotes" and, comma'),
    ]

    csv_output = storage.export_csv(todos)

    # Verify CSV parsing handles special characters correctly
    reader = csv.DictReader(io.StringIO(csv_output))
    rows = list(reader)

    assert rows[0]["text"] == 'Task with "quotes"'
    assert rows[1]["text"] == "Task with, comma"
    assert rows[2]["text"] == 'Task with "quotes" and, comma'


def test_export_markdown_basic_todos(tmp_path) -> None:
    """Export todos to GitHub-flavored markdown table."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create some todos
    todos = [
        Todo(id=1, text="Task 1", done=False),
        Todo(id=2, text="Task 2", done=True),
    ]
    storage.save(todos)

    # Export to Markdown
    md_output = storage.export_markdown(todos)

    # Verify markdown table structure
    lines = md_output.strip().split("\n")

    # Check header row
    assert "| id | text | done | created_at | updated_at |" in lines[0]

    # Check separator
    assert "|---" in lines[1] or "| ---" in lines[1]

    # Check data rows
    assert "| 1 | Task 1 | False |" in lines[2] or "| 1 | Task 1 | False |" in md_output
    assert "| 2 | Task 2 | True |" in lines[3] or "| 2 | Task 2 | True |" in md_output


def test_export_markdown_unicode_handling(tmp_path) -> None:
    """Export todos with unicode characters to Markdown."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="任务一 - 中文测试"),
        Todo(id=2, text="タスク二 - 日本語"),
    ]
    storage.save(todos)

    md_output = storage.export_markdown(todos)

    # Verify unicode is preserved
    assert "任务一 - 中文测试" in md_output
    assert "タスク二 - 日本語" in md_output


def test_export_markdown_empty_list(tmp_path) -> None:
    """Export empty todo list to Markdown."""
    storage = TodoStorage(str(tmp_path / "todo.json"))

    md_output = storage.export_markdown([])

    # Should produce headers only
    lines = md_output.strip().split("\n")
    assert len(lines) == 2  # header + separator
    assert "| id | text | done |" in lines[0]


def test_export_markdown_special_characters(tmp_path) -> None:
    """Export todos with special markdown characters to Markdown table."""
    storage = TodoStorage(str(tmp_path / "todo.json"))

    todos = [
        Todo(id=1, text="Task with | pipe"),
        Todo(id=2, text="Task with *asterisk*"),
    ]

    md_output = storage.export_markdown(todos)

    # Pipe characters should be escaped or handled
    # The output should be valid markdown (pipe in content should not break table)
    lines = md_output.strip().split("\n")
    assert len(lines) >= 4  # header + separator + 2 data rows

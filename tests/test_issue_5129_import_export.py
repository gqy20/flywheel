"""Tests for import/export functionality in TodoStorage.

This test suite verifies that TodoStorage supports importing and exporting
todos in JSON and CSV formats for interoperability with external tools.

Issue: #5129
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestExportToJSON:
    """Tests for export_to() method with JSON format."""

    def test_export_to_json_creates_file(self, tmp_path: Path) -> None:
        """export_to() should create a file at the specified path."""
        db = tmp_path / "todo.json"
        export_path = tmp_path / "export.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task 1"), Todo(id=2, text="task 2", done=True)]
        storage.save(todos)

        storage.export_to(export_path, format="json")
        assert export_path.exists()

    def test_export_to_json_produces_valid_json(self, tmp_path: Path) -> None:
        """export_to() should produce valid, parseable JSON."""
        db = tmp_path / "todo.json"
        export_path = tmp_path / "export.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task with unicode: 你好")]
        storage.save(todos)

        storage.export_to(export_path, format="json")

        content = export_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert len(parsed) == 1
        assert parsed[0]["text"] == "task with unicode: 你好"

    def test_export_to_json_default_format(self, tmp_path: Path) -> None:
        """export_to() should default to JSON format."""
        db = tmp_path / "todo.json"
        export_path = tmp_path / "export.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="default format test")]
        storage.save(todos)

        storage.export_to(export_path)  # No format specified
        content = export_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert len(parsed) == 1

    def test_export_to_json_includes_all_fields(self, tmp_path: Path) -> None:
        """export_to() should include all todo fields."""
        db = tmp_path / "todo.json"
        export_path = tmp_path / "export.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="complete task", done=True)]
        storage.save(todos)

        storage.export_to(export_path, format="json")
        content = export_path.read_text(encoding="utf-8")
        parsed = json.loads(content)

        assert parsed[0]["id"] == 1
        assert parsed[0]["text"] == "complete task"
        assert parsed[0]["done"] is True
        assert "created_at" in parsed[0]
        assert "updated_at" in parsed[0]


class TestExportToCSV:
    """Tests for export_to() method with CSV format."""

    def test_export_to_csv_creates_file(self, tmp_path: Path) -> None:
        """export_to() should create a CSV file at the specified path."""
        db = tmp_path / "todo.json"
        export_path = tmp_path / "export.csv"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task 1")]
        storage.save(todos)

        storage.export_to(export_path, format="csv")
        assert export_path.exists()

    def test_export_to_csv_has_correct_headers(self, tmp_path: Path) -> None:
        """export_to() CSV should have proper column headers."""
        db = tmp_path / "todo.json"
        export_path = tmp_path / "export.csv"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task")]
        storage.save(todos)

        storage.export_to(export_path, format="csv")

        with open(export_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            assert "id" in headers
            assert "text" in headers
            assert "done" in headers

    def test_export_to_csv_has_correct_data(self, tmp_path: Path) -> None:
        """export_to() CSV should contain correct todo data."""
        db = tmp_path / "todo.json"
        export_path = tmp_path / "export.csv"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="task one", done=False),
            Todo(id=2, text="task two", done=True),
        ]
        storage.save(todos)

        storage.export_to(export_path, format="csv")

        with open(export_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["id"] == "1"
        assert rows[0]["text"] == "task one"
        assert rows[0]["done"] == "False"
        assert rows[1]["id"] == "2"
        assert rows[1]["text"] == "task two"
        assert rows[1]["done"] == "True"

    def test_export_to_csv_handles_special_characters(self, tmp_path: Path) -> None:
        """export_to() CSV should handle commas and quotes in text."""
        db = tmp_path / "todo.json"
        export_path = tmp_path / "export.csv"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text='task with "quotes" and, commas')]
        storage.save(todos)

        storage.export_to(export_path, format="csv")

        with open(export_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert rows[0]["text"] == 'task with "quotes" and, commas'


class TestImportFromJSON:
    """Tests for import_from() method with JSON format."""

    def test_import_from_json_loads_todos(self, tmp_path: Path) -> None:
        """import_from() should load todos from a JSON file."""
        db = tmp_path / "todo.json"
        import_path = tmp_path / "import.json"
        storage = TodoStorage(str(db))

        # Create import file
        import_data = [{"id": 1, "text": "imported task", "done": False}]
        import_path.write_text(json.dumps(import_data), encoding="utf-8")

        todos = storage.import_from(import_path, format="json")
        assert len(todos) == 1
        assert todos[0].text == "imported task"

    def test_import_from_json_default_format(self, tmp_path: Path) -> None:
        """import_from() should default to JSON format."""
        db = tmp_path / "todo.json"
        import_path = tmp_path / "import.json"
        storage = TodoStorage(str(db))

        import_data = [{"id": 1, "text": "default json"}]
        import_path.write_text(json.dumps(import_data), encoding="utf-8")

        todos = storage.import_from(import_path)  # No format specified
        assert len(todos) == 1

    def test_import_from_json_merges_with_existing(self, tmp_path: Path) -> None:
        """import_from() should merge imported todos with existing ones."""
        db = tmp_path / "todo.json"
        import_path = tmp_path / "import.json"
        storage = TodoStorage(str(db))

        # Save existing todos
        existing = [Todo(id=1, text="existing")]
        storage.save(existing)

        # Import new todos
        import_data = [{"id": 2, "text": "imported", "done": True}]
        import_path.write_text(json.dumps(import_data), encoding="utf-8")

        storage.import_from(import_path, format="json")

        loaded = storage.load()
        assert len(loaded) == 2

    def test_import_from_json_invalid_format_raises_error(self, tmp_path: Path) -> None:
        """import_from() should raise ValueError for invalid JSON."""
        db = tmp_path / "todo.json"
        import_path = tmp_path / "invalid.json"
        storage = TodoStorage(str(db))

        import_path.write_text("not valid json", encoding="utf-8")

        with pytest.raises(ValueError, match=r"[Ii]nvalid"):
            storage.import_from(import_path, format="json")

    def test_import_from_json_missing_required_field_raises_error(self, tmp_path: Path) -> None:
        """import_from() should raise ValueError for missing required fields."""
        db = tmp_path / "todo.json"
        import_path = tmp_path / "missing_field.json"
        storage = TodoStorage(str(db))

        import_data = [{"id": 1}]  # Missing 'text'
        import_path.write_text(json.dumps(import_data), encoding="utf-8")

        with pytest.raises(ValueError, match=r"[Mm]issing"):
            storage.import_from(import_path, format="json")


class TestImportFromCSV:
    """Tests for import_from() method with CSV format."""

    def test_import_from_csv_loads_todos(self, tmp_path: Path) -> None:
        """import_from() should load todos from a CSV file."""
        db = tmp_path / "todo.json"
        import_path = tmp_path / "import.csv"
        storage = TodoStorage(str(db))

        # Create import file
        with open(import_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "text", "done"])
            writer.writerow([1, "csv task", "False"])

        todos = storage.import_from(import_path, format="csv")
        assert len(todos) == 1
        assert todos[0].text == "csv task"
        assert todos[0].done is False

    def test_import_from_csv_handles_boolean_values(self, tmp_path: Path) -> None:
        """import_from() should parse boolean 'done' values correctly."""
        db = tmp_path / "todo.json"
        import_path = tmp_path / "import.csv"
        storage = TodoStorage(str(db))

        with open(import_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "text", "done"])
            writer.writerow([1, "done task", "True"])
            writer.writerow([2, "pending task", "False"])

        todos = storage.import_from(import_path, format="csv")
        assert todos[0].done is True
        assert todos[1].done is False

    def test_import_from_csv_invalid_format_raises_error(self, tmp_path: Path) -> None:
        """import_from() should raise ValueError for invalid CSV."""
        db = tmp_path / "todo.json"
        import_path = tmp_path / "invalid.csv"
        storage = TodoStorage(str(db))

        import_path.write_text("not,valid,csv\nwithout,proper,structure", encoding="utf-8")

        with pytest.raises(ValueError):
            storage.import_from(import_path, format="csv")


class TestImportExportRoundtrip:
    """Tests for export then import data consistency."""

    def test_json_roundtrip_preserves_data(self, tmp_path: Path) -> None:
        """Export to JSON and re-import should preserve all data."""
        db = tmp_path / "todo.json"
        export_path = tmp_path / "export.json"
        storage = TodoStorage(str(db))

        original_todos = [
            Todo(id=1, text="task one", done=False),
            Todo(id=2, text="task two", done=True),
            Todo(id=3, text="task three"),
        ]
        storage.save(original_todos)

        # Export
        storage.export_to(export_path, format="json")

        # Clear and import
        storage.save([])
        imported = storage.import_from(export_path, format="json")

        assert len(imported) == 3
        assert imported[0].text == "task one"
        assert imported[1].done is True
        assert imported[2].text == "task three"

    def test_csv_roundtrip_preserves_data(self, tmp_path: Path) -> None:
        """Export to CSV and re-import should preserve core data."""
        db = tmp_path / "todo.json"
        export_path = tmp_path / "export.csv"
        storage = TodoStorage(str(db))

        original_todos = [
            Todo(id=1, text="csv task one", done=False),
            Todo(id=2, text="csv task two", done=True),
        ]
        storage.save(original_todos)

        # Export
        storage.export_to(export_path, format="csv")

        # Clear and import
        storage.save([])
        imported = storage.import_from(export_path, format="csv")

        assert len(imported) == 2
        assert imported[0].text == "csv task one"
        assert imported[0].done is False
        assert imported[1].text == "csv task two"
        assert imported[1].done is True


class TestUnsupportedFormat:
    """Tests for unsupported format handling."""

    def test_export_to_unsupported_format_raises_error(self, tmp_path: Path) -> None:
        """export_to() should raise ValueError for unsupported formats."""
        db = tmp_path / "todo.json"
        export_path = tmp_path / "export.xml"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="task")]
        storage.save(todos)

        with pytest.raises(ValueError, match=r"[Uu]nsupported.*format"):
            storage.export_to(export_path, format="xml")

    def test_import_from_unsupported_format_raises_error(self, tmp_path: Path) -> None:
        """import_from() should raise ValueError for unsupported formats."""
        db = tmp_path / "todo.json"
        import_path = tmp_path / "import.xml"
        storage = TodoStorage(str(db))

        import_path.write_text("<todos><todo>test</todo></todos>", encoding="utf-8")

        with pytest.raises(ValueError, match=r"[Uu]nsupported.*format"):
            storage.import_from(import_path, format="xml")

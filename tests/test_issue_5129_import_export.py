"""Tests for data import/export functionality in TodoStorage.

This test suite verifies the export_to() and import_from() methods that allow
users to export their todo data to external files and import from them.

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
    """Tests for TodoStorage.export_to() with JSON format."""

    def test_export_to_json_creates_valid_file(self, tmp_path: Path) -> None:
        """Test that export_to creates a valid JSON file."""
        db = tmp_path / "todo.json"
        export_file = tmp_path / "export.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="Buy groceries", done=False),
            Todo(id=2, text="Walk dog", done=True),
        ]
        storage.save(todos)

        storage.export_to(export_file, format="json")

        assert export_file.exists()
        content = json.loads(export_file.read_text(encoding="utf-8"))
        assert len(content) == 2
        assert content[0]["text"] == "Buy groceries"
        assert content[1]["done"] is True

    def test_export_to_json_default_format(self, tmp_path: Path) -> None:
        """Test that JSON is the default format."""
        db = tmp_path / "todo.json"
        export_file = tmp_path / "export.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="Test")]
        storage.save(todos)

        storage.export_to(export_file)  # No format specified

        content = json.loads(export_file.read_text(encoding="utf-8"))
        assert len(content) == 1


class TestExportToCSV:
    """Tests for TodoStorage.export_to() with CSV format."""

    def test_export_to_csv_creates_valid_file(self, tmp_path: Path) -> None:
        """Test that export_to creates a valid CSV file."""
        db = tmp_path / "todo.json"
        export_file = tmp_path / "export.csv"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="Buy groceries", done=False),
            Todo(id=2, text="Walk dog", done=True),
        ]
        storage.save(todos)

        storage.export_to(export_file, format="csv")

        assert export_file.exists()
        with open(export_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["text"] == "Buy groceries"
            assert rows[1]["done"] == "True"


class TestImportFromJSON:
    """Tests for TodoStorage.import_from() with JSON format."""

    def test_import_from_json_restores_todos(self, tmp_path: Path) -> None:
        """Test that import_from restores todos from a JSON file."""
        db = tmp_path / "todo.json"
        import_file = tmp_path / "import.json"
        storage = TodoStorage(str(db))

        # Create import file
        import_data = [
            {"id": 10, "text": "Imported task 1", "done": False},
            {"id": 11, "text": "Imported task 2", "done": True},
        ]
        import_file.write_text(json.dumps(import_data), encoding="utf-8")

        imported = storage.import_from(import_file, format="json")

        assert len(imported) == 2
        assert imported[0].id == 10
        assert imported[0].text == "Imported task 1"
        assert imported[1].done is True

    def test_import_from_json_default_format(self, tmp_path: Path) -> None:
        """Test that JSON is the default format for import."""
        db = tmp_path / "todo.json"
        import_file = tmp_path / "import.json"
        storage = TodoStorage(str(db))

        import_data = [{"id": 1, "text": "Task"}]
        import_file.write_text(json.dumps(import_data), encoding="utf-8")

        imported = storage.import_from(import_file)  # No format specified

        assert len(imported) == 1


class TestImportFromCSV:
    """Tests for TodoStorage.import_from() with CSV format."""

    def test_import_from_csv_restores_todos(self, tmp_path: Path) -> None:
        """Test that import_from restores todos from a CSV file."""
        db = tmp_path / "todo.json"
        import_file = tmp_path / "import.csv"
        storage = TodoStorage(str(db))

        # Create import file
        with open(import_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["id", "text", "done", "created_at", "updated_at"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "id": "20",
                    "text": "CSV task 1",
                    "done": "False",
                    "created_at": "",
                    "updated_at": "",
                }
            )
            writer.writerow(
                {
                    "id": "21",
                    "text": "CSV task 2",
                    "done": "True",
                    "created_at": "",
                    "updated_at": "",
                }
            )

        imported = storage.import_from(import_file, format="csv")

        assert len(imported) == 2
        assert imported[0].id == 20
        assert imported[0].text == "CSV task 1"
        assert imported[1].done is True


class TestImportValidation:
    """Tests for import validation and error handling."""

    def test_import_invalid_format_raises_value_error(self, tmp_path: Path) -> None:
        """Test that invalid format raises ValueError."""
        db = tmp_path / "todo.json"
        import_file = tmp_path / "import.xml"
        storage = TodoStorage(str(db))

        import_file.write_text("<todos></todos>", encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported format"):
            storage.import_from(import_file, format="xml")

    def test_import_malformed_json_raises_value_error(self, tmp_path: Path) -> None:
        """Test that malformed JSON raises clear error."""
        db = tmp_path / "todo.json"
        import_file = tmp_path / "import.json"
        storage = TodoStorage(str(db))

        import_file.write_text("{ not valid json }", encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid JSON"):
            storage.import_from(import_file, format="json")

    def test_export_invalid_format_raises_value_error(self, tmp_path: Path) -> None:
        """Test that invalid export format raises ValueError."""
        db = tmp_path / "todo.json"
        export_file = tmp_path / "export.xml"
        storage = TodoStorage(str(db))

        storage.save([Todo(id=1, text="Test")])

        with pytest.raises(ValueError, match="Unsupported format"):
            storage.export_to(export_file, format="xml")


class TestImportMergeStrategy:
    """Tests for import merge vs replace behavior."""

    def test_import_merges_by_default(self, tmp_path: Path) -> None:
        """Test that import merges with existing todos by default."""
        db = tmp_path / "todo.json"
        import_file = tmp_path / "import.json"
        storage = TodoStorage(str(db))

        # Existing todos
        storage.save([Todo(id=1, text="Existing task")])

        # Import file with new todo
        import_data = [{"id": 2, "text": "Imported task", "done": False}]
        import_file.write_text(json.dumps(import_data), encoding="utf-8")

        imported = storage.import_from(import_file)

        # Should return only imported todos
        assert len(imported) == 1
        assert imported[0].text == "Imported task"

        # Storage should have both
        all_todos = storage.load()
        assert len(all_todos) == 2

    def test_import_replaces_when_merge_false(self, tmp_path: Path) -> None:
        """Test that import replaces all todos when merge=False."""
        db = tmp_path / "todo.json"
        import_file = tmp_path / "import.json"
        storage = TodoStorage(str(db))

        # Existing todos
        storage.save([Todo(id=1, text="Existing task")])

        # Import file with new todo
        import_data = [{"id": 2, "text": "Imported task", "done": False}]
        import_file.write_text(json.dumps(import_data), encoding="utf-8")

        imported = storage.import_from(import_file, merge=False)

        # Should return imported todos
        assert len(imported) == 1
        assert imported[0].text == "Imported task"

        # Storage should only have imported todo
        all_todos = storage.load()
        assert len(all_todos) == 1
        assert all_todos[0].text == "Imported task"

    def test_import_handles_id_conflicts_with_reassignment(self, tmp_path: Path) -> None:
        """Test that import handles ID conflicts by reassigning IDs."""
        db = tmp_path / "todo.json"
        import_file = tmp_path / "import.json"
        storage = TodoStorage(str(db))

        # Existing todo with id=1
        storage.save([Todo(id=1, text="Existing task")])

        # Import file also has id=1
        import_data = [{"id": 1, "text": "Imported task", "done": False}]
        import_file.write_text(json.dumps(import_data), encoding="utf-8")

        imported = storage.import_from(import_file, merge=True)

        # Imported todo should get a new ID
        assert imported[0].id != 1
        assert imported[0].text == "Imported task"

        # Both should exist in storage
        all_todos = storage.load()
        assert len(all_todos) == 2

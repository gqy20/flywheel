"""Tests for data import/export functionality (Issue #5129).

This test suite verifies that TodoStorage supports importing and exporting
data in JSON and CSV formats for interoperability with other tools.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestExportTo:
    """Tests for TodoStorage.export_to() method."""

    def test_export_to_json_creates_valid_file(self, tmp_path: Path) -> None:
        """Export to JSON should create a valid JSON file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="task one", done=False),
            Todo(id=2, text="task two", done=True),
        ]
        storage.save(todos)

        export_path = tmp_path / "export.json"
        storage.export_to(export_path, format="json")

        # Verify file exists and contains valid JSON
        assert export_path.exists()
        content = json.loads(export_path.read_text(encoding="utf-8"))
        assert len(content) == 2
        assert content[0]["text"] == "task one"
        assert content[1]["done"] is True

    def test_export_to_json_default_format(self, tmp_path: Path) -> None:
        """Export without format parameter should default to JSON."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        export_path = tmp_path / "export.json"
        storage.export_to(export_path)  # No format specified

        content = json.loads(export_path.read_text(encoding="utf-8"))
        assert len(content) == 1

    def test_export_to_csv_creates_valid_file(self, tmp_path: Path) -> None:
        """Export to CSV should create a valid CSV file with proper headers."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="csv task", done=False),
            Todo(id=2, text="done task", done=True),
        ]
        storage.save(todos)

        export_path = tmp_path / "export.csv"
        storage.export_to(export_path, format="csv")

        # Verify file exists and contains valid CSV
        assert export_path.exists()
        with open(export_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["id"] == "1"
        assert rows[0]["text"] == "csv task"
        assert rows[0]["done"] == "False"
        assert rows[1]["done"] == "True"

    def test_export_to_creates_parent_directory(self, tmp_path: Path) -> None:
        """Export should create parent directories if they don't exist."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        export_path = tmp_path / "subdir" / "deep" / "export.json"
        storage.export_to(export_path, format="json")

        assert export_path.exists()

    def test_export_to_unsupported_format_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Export to unsupported format should raise ValueError."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        export_path = tmp_path / "export.xml"
        with pytest.raises(ValueError, match="Unsupported format"):
            storage.export_to(export_path, format="xml")

    def test_export_to_empty_todos(self, tmp_path: Path) -> None:
        """Export with no todos should create valid empty file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        # Don't save any todos

        export_path = tmp_path / "export.json"
        storage.export_to(export_path, format="json")

        content = json.loads(export_path.read_text(encoding="utf-8"))
        assert content == []

    def test_export_to_csv_empty_todos(self, tmp_path: Path) -> None:
        """Export to CSV with no todos should create file with headers only."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        export_path = tmp_path / "export.csv"
        storage.export_to(export_path, format="csv")

        with open(export_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 0
        # Headers should still be present
        assert reader.fieldnames == ["id", "text", "done", "created_at", "updated_at"]


class TestImportFrom:
    """Tests for TodoStorage.import_from() method."""

    def test_import_from_json_merges_data(self, tmp_path: Path) -> None:
        """Import from JSON should merge with existing data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create some existing todos
        existing = [Todo(id=1, text="existing")]
        storage.save(existing)

        # Create import file
        import_path = tmp_path / "import.json"
        import_data = [
            {"id": 2, "text": "imported task", "done": False},
            {"id": 3, "text": "another task", "done": True},
        ]
        import_path.write_text(json.dumps(import_data), encoding="utf-8")

        # Import with merge mode
        storage.import_from(import_path, format="json", mode="merge")

        loaded = storage.load()
        assert len(loaded) == 3

    def test_import_from_json_replace_data(self, tmp_path: Path) -> None:
        """Import from JSON with replace mode should replace all data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create some existing todos
        existing = [Todo(id=1, text="existing"), Todo(id=2, text="old")]
        storage.save(existing)

        # Create import file
        import_path = tmp_path / "import.json"
        import_data = [{"id": 10, "text": "new task", "done": False}]
        import_path.write_text(json.dumps(import_data), encoding="utf-8")

        # Import with replace mode
        storage.import_from(import_path, format="json", mode="replace")

        loaded = storage.load()
        assert len(loaded) == 1
        # IDs are reassigned starting from 1 in replace mode
        assert loaded[0].id == 1
        assert loaded[0].text == "new task"

    def test_import_from_json_default_mode_is_merge(
        self, tmp_path: Path
    ) -> None:
        """Import without mode should default to merge."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        existing = [Todo(id=1, text="existing")]
        storage.save(existing)

        import_path = tmp_path / "import.json"
        import_data = [{"id": 2, "text": "imported"}]
        import_path.write_text(json.dumps(import_data), encoding="utf-8")

        storage.import_from(import_path, format="json")

        loaded = storage.load()
        assert len(loaded) == 2

    def test_import_from_csv(self, tmp_path: Path) -> None:
        """Import from CSV should correctly parse data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create CSV import file
        import_path = tmp_path / "import.csv"
        with open(import_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "text", "done", "created_at", "updated_at"])
            writer.writerow([1, "csv task", "False", "", ""])
            writer.writerow([2, "done csv task", "True", "", ""])

        storage.import_from(import_path, format="csv", mode="replace")

        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "csv task"
        assert loaded[0].done is False
        assert loaded[1].done is True

    def test_import_from_json_reassigns_ids(self, tmp_path: Path) -> None:
        """Import should reassign IDs to avoid conflicts."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        existing = [Todo(id=1, text="existing")]
        storage.save(existing)

        import_path = tmp_path / "import.json"
        # Import has id=1 which conflicts with existing
        import_data = [{"id": 1, "text": "imported", "done": False}]
        import_path.write_text(json.dumps(import_data), encoding="utf-8")

        storage.import_from(import_path, format="json", mode="merge")

        loaded = storage.load()
        assert len(loaded) == 2
        # IDs should be unique
        ids = [t.id for t in loaded]
        assert len(ids) == len(set(ids))

    def test_import_from_invalid_json_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Import from invalid JSON should raise ValueError."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        import_path = tmp_path / "import.json"
        import_path.write_text("not valid json {", encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid JSON"):
            storage.import_from(import_path, format="json")

    def test_import_from_invalid_csv_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Import from CSV missing required columns should raise ValueError."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        import_path = tmp_path / "import.csv"
        with open(import_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["wrong", "columns"])  # Missing 'id' and 'text'
            writer.writerow(["value1", "value2"])

        with pytest.raises(ValueError, match="Missing required column"):
            storage.import_from(import_path, format="csv")

    def test_import_from_missing_file_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Import from non-existent file should raise FileNotFoundError."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        import_path = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            storage.import_from(import_path, format="json")

    def test_import_from_unsupported_format_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Import from unsupported format should raise ValueError."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        import_path = tmp_path / "import.xml"
        import_path.write_text("<data></data>", encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported format"):
            storage.import_from(import_path, format="xml")


class TestRoundTrip:
    """Tests for export then import data consistency."""

    def test_json_roundtrip_preserves_data(self, tmp_path: Path) -> None:
        """Export to JSON then import should preserve all data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        original_todos = [
            Todo(id=1, text="task one", done=False),
            Todo(id=2, text="task two", done=True),
            Todo(id=3, text="unicode: 你好世界", done=False),
        ]
        storage.save(original_todos)

        # Export
        export_path = tmp_path / "export.json"
        storage.export_to(export_path, format="json")

        # Clear and import
        new_db = tmp_path / "new_todo.json"
        new_storage = TodoStorage(str(new_db))
        new_storage.import_from(export_path, format="json", mode="replace")

        loaded = new_storage.load()
        assert len(loaded) == len(original_todos)

        # Check each todo (excluding timestamps which may differ)
        for orig, imp in zip(original_todos, loaded, strict=True):
            assert imp.text == orig.text
            assert imp.done == orig.done

    def test_csv_roundtrip_preserves_data(self, tmp_path: Path) -> None:
        """Export to CSV then import should preserve core data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        original_todos = [
            Todo(id=1, text="csv task", done=False),
            Todo(id=2, text="done task", done=True),
        ]
        storage.save(original_todos)

        # Export to CSV
        export_path = tmp_path / "export.csv"
        storage.export_to(export_path, format="csv")

        # Clear and import
        new_db = tmp_path / "new_todo.json"
        new_storage = TodoStorage(str(new_db))
        new_storage.import_from(export_path, format="csv", mode="replace")

        loaded = new_storage.load()
        assert len(loaded) == len(original_todos)

        for orig, imp in zip(original_todos, loaded, strict=True):
            assert imp.text == orig.text
            assert imp.done == orig.done

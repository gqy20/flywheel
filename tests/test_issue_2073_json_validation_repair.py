"""Tests for JSON file validation and repair methods (Issue #2073).

These tests verify that:
1. validate() returns True for valid JSON file
2. validate() returns False with useful error for truncated JSON
3. repair() extracts valid todos from file with trailing comma
4. repair() handles completely invalid JSON gracefully
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestValidateMethod:
    """Tests for TodoStorage.validate() method."""

    def test_validate_returns_true_for_valid_json(self, tmp_path) -> None:
        """validate() should return True for valid JSON file."""
        db = tmp_path / "valid.json"
        storage = TodoStorage(str(db))

        # Create valid JSON file
        todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
        storage.save(todos)

        # Validate should return True with no error
        is_valid, error = storage.validate()
        assert is_valid is True
        assert error is None

    def test_validate_returns_false_for_truncated_json(self, tmp_path) -> None:
        """validate() should return False with useful error for truncated JSON."""
        db = tmp_path / "truncated.json"
        storage = TodoStorage(str(db))

        # Create truncated JSON file (missing closing bracket)
        db.write_text('[{"id": 1, "text": "task1"}', encoding="utf-8")

        # Validate should return False with error message
        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None
        assert "json" in error.lower() or "parse" in error.lower()

    def test_validate_returns_false_for_invalid_json(self, tmp_path) -> None:
        """validate() should return False with useful error for invalid JSON."""
        db = tmp_path / "invalid.json"
        storage = TodoStorage(str(db))

        # Create completely invalid JSON
        db.write_text('not json at all', encoding="utf-8")

        # Validate should return False with error message
        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None

    def test_validate_returns_false_for_trailing_comma(self, tmp_path) -> None:
        """validate() should return False for JSON with trailing comma."""
        db = tmp_path / "trailing_comma.json"
        storage = TodoStorage(str(db))

        # Create JSON with trailing comma (not valid strict JSON)
        db.write_text('[{"id": 1, "text": "task1"},]', encoding="utf-8")

        # Validate should return False with error message
        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None

    def test_validate_returns_true_for_nonexistent_file(self, tmp_path) -> None:
        """validate() should return True for nonexistent file (empty state)."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # Nonexistent file is considered valid (empty state)
        is_valid, error = storage.validate()
        assert is_valid is True
        assert error is None


class TestRepairMethod:
    """Tests for TodoStorage.repair() method."""

    def test_repair_extracts_valid_todos_from_trailing_comma(self, tmp_path) -> None:
        """repair() should extract valid todos from file with trailing comma."""
        db = tmp_path / "trailing_comma.json"
        backup = tmp_path / "trailing_comma.json.recovered.json"
        storage = TodoStorage(str(db))

        # Create JSON with trailing comma
        db.write_text('[{"id": 1, "text": "task1"},]', encoding="utf-8")

        # Repair should extract valid todos
        repaired_todos = storage.repair()

        # Should have extracted the valid todo
        assert len(repaired_todos) == 1
        assert repaired_todos[0].id == 1
        assert repaired_todos[0].text == "task1"

        # Backup file should be created
        assert backup.exists()

    def test_repair_handles_truncated_json(self, tmp_path) -> None:
        """repair() should attempt to extract valid todos from truncated JSON."""
        db = tmp_path / "truncated.json"
        backup = tmp_path / "truncated.json.recovered.json"
        storage = TodoStorage(str(db))

        # Create truncated JSON
        db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"', encoding="utf-8")

        # Repair should extract what it can
        repaired_todos = storage.repair()

        # Should have extracted the first complete todo
        assert len(repaired_todos) >= 1
        assert repaired_todos[0].id == 1
        assert repaired_todos[0].text == "task1"

        # Backup file should be created
        assert backup.exists()

    def test_repair_handles_completely_invalid_json(self, tmp_path) -> None:
        """repair() should gracefully handle completely invalid JSON."""
        db = tmp_path / "invalid.json"
        backup = tmp_path / "invalid.json.recovered.json"
        storage = TodoStorage(str(db))

        # Create completely invalid content
        db.write_text('totally not json {{{', encoding="utf-8")

        # Repair should return empty list (no valid todos found)
        repaired_todos = storage.repair()
        assert repaired_todos == []

        # Backup file should still be created
        assert backup.exists()

    def test_repair_creates_backup_before_modifying(self, tmp_path) -> None:
        """repair() should create .recovered.json backup before attempting repairs."""
        db = tmp_path / "corrupt.json"
        backup = tmp_path / "corrupt.json.recovered.json"
        storage = TodoStorage(str(db))

        # Create corrupted content
        original_content = '[{"id": 1, "text": "task1"},'
        db.write_text(original_content, encoding="utf-8")

        # Repair
        storage.repair()

        # Backup should contain original corrupted content
        backup_content = backup.read_text(encoding="utf-8")
        assert backup_content == original_content

    def test_repair_saves_repaired_data_to_file(self, tmp_path) -> None:
        """repair() should save repaired data to the original file."""
        db = tmp_path / "corrupt.json"
        storage = TodoStorage(str(db))

        # Create corrupted content with one valid todo
        db.write_text('[{"id": 1, "text": "task1"},]', encoding="utf-8")

        # Repair
        repaired_todos = storage.repair()

        # File should now contain valid JSON with repaired todos
        loaded = storage.load()
        assert len(loaded) == len(repaired_todos)
        assert loaded[0].id == 1
        assert loaded[0].text == "task1"

    def test_repair_with_valid_json_does_nothing(self, tmp_path) -> None:
        """repair() with already valid JSON should not modify the file."""
        db = tmp_path / "valid.json"
        storage = TodoStorage(str(db))

        # Create valid JSON
        original_todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
        storage.save(original_todos)
        original_content = db.read_text(encoding="utf-8")

        # Repair should not change anything
        repaired_todos = storage.repair()

        assert len(repaired_todos) == 2
        assert db.read_text(encoding="utf-8") == original_content

    def test_repair_handles_empty_array(self, tmp_path) -> None:
        """repair() should handle empty JSON array."""
        db = tmp_path / "empty.json"
        storage = TodoStorage(str(db))

        # Create empty JSON array
        db.write_text('[]', encoding="utf-8")

        # Repair should return empty list
        repaired_todos = storage.repair()
        assert repaired_todos == []

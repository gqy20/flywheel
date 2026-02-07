"""Tests for JSON validation and repair functionality - Issue #2073.

This test suite verifies that TodoStorage can validate and repair corrupted JSON files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestValidateMethod:
    """Tests for TodoStorage.validate() method."""

    def test_validate_returns_true_for_valid_json_file(self, tmp_path) -> None:
        """Test validate() returns True for valid JSON file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a valid JSON file
        todos = [Todo(id=1, text="valid todo")]
        storage.save(todos)

        # Validate should return True with no error message
        is_valid, error = storage.validate()
        assert is_valid is True
        assert error is None

    def test_validate_returns_true_for_nonexistent_file(self, tmp_path) -> None:
        """Test validate() returns True for nonexistent file (empty state is valid)."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # Nonexistent file is considered valid (will be created on first save)
        is_valid, error = storage.validate()
        assert is_valid is True
        assert error is None

    def test_validate_returns_false_for_truncated_json(self, tmp_path) -> None:
        """Test validate() returns False with useful error for truncated JSON."""
        db = tmp_path / "truncated.json"
        storage = TodoStorage(str(db))

        # Create a truncated JSON file
        db.write_text('[{"id": 1, "text": "todo"}, {"id": 2, "text": "incomplete"')

        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None
        assert "JSON" in error.lower() or "invalid" in error.lower()

    def test_validate_returns_false_for_invalid_json_structure(self, tmp_path) -> None:
        """Test validate() returns False for non-list JSON structure."""
        db = tmp_path / "invalid_structure.json"
        storage = TodoStorage(str(db))

        # Create a JSON file that's not a list
        db.write_text('{"id": 1, "text": "not a list"}')

        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None
        assert "list" in error.lower()

    def test_validate_returns_false_for_trailing_comma(self, tmp_path) -> None:
        """Test validate() returns False for JSON with trailing comma."""
        db = tmp_path / "trailing_comma.json"
        storage = TodoStorage(str(db))

        # Create JSON with trailing comma (invalid in strict JSON)
        db.write_text('[{"id": 1, "text": "todo"},]')

        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None


class TestRepairMethod:
    """Tests for TodoStorage.repair() method."""

    def test_repair_creates_backup_before_repair(self, tmp_path) -> None:
        """Test repair() creates .recovered.json backup before attempting repair."""
        db = tmp_path / "corrupted.json"
        storage = TodoStorage(str(db))

        # Create corrupted JSON
        db.write_text('[{"id": 1, "text": "valid"}, {"id": 2, "text": "incomplete"')

        backup_path = tmp_path / "corrupted.json.recovered.json"

        # Verify backup doesn't exist yet
        assert not backup_path.exists()

        # Repair should create backup
        repaired = storage.repair()

        # Backup should exist
        assert backup_path.exists()
        # Backup should contain original corrupted content
        assert backup_path.read_text() == '[{"id": 1, "text": "valid"}, {"id": 2, "text": "incomplete"'

    def test_repair_extracts_valid_todos_from_trailing_comma(self, tmp_path) -> None:
        """Test repair() extracts valid todos from file with trailing comma."""
        db = tmp_path / "trailing_comma.json"
        storage = TodoStorage(str(db))

        # Create JSON with trailing comma (common manual edit error)
        db.write_text('[{"id": 1, "text": "first"}, {"id": 2, "text": "second"},]')

        repaired = storage.repair()

        assert repaired is True
        # Should be able to load after repair
        todos = storage.load()
        assert len(todos) == 2
        assert todos[0].text == "first"
        assert todos[1].text == "second"

    def test_repair_handles_truncated_json_by_extracting_complete_objects(self, tmp_path) -> None:
        """Test repair() extracts complete objects from truncated JSON."""
        db = tmp_path / "truncated.json"
        storage = TodoStorage(str(db))

        # Create truncated JSON - last todo is incomplete
        db.write_text('[{"id": 1, "text": "complete"}, {"id": 2, "text": "incomplete"')

        repaired = storage.repair()

        assert repaired is True
        # Should extract the complete todo
        todos = storage.load()
        assert len(todos) >= 1
        assert todos[0].text == "complete"

    def test_repair_returns_false_for_completely_invalid_json(self, tmp_path) -> None:
        """Test repair() returns False for completely invalid JSON."""
        db = tmp_path / "invalid.json"
        storage = TodoStorage(str(db))

        # Create completely invalid content
        db.write_text('this is not json at all')

        repaired = storage.repair()

        assert repaired is False
        # File should contain empty list after failed repair
        todos = storage.load()
        assert len(todos) == 0

    def test_repair_handles_valid_json_gracefully(self, tmp_path) -> None:
        """Test repair() handles already-valid JSON gracefully."""
        db = tmp_path / "valid.json"
        storage = TodoStorage(str(db))

        # Create valid JSON
        todos = [Todo(id=1, text="valid"), Todo(id=2, text="data")]
        storage.save(todos)

        # Repair should still work
        repaired = storage.repair()

        assert repaired is True
        # Data should be unchanged
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "valid"
        assert loaded[1].text == "data"

    def test_repair_creates_empty_list_for_nonexistent_file(self, tmp_path) -> None:
        """Test repair() creates empty list for nonexistent file."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # File doesn't exist
        assert not db.exists()

        # Repair should create valid empty file
        repaired = storage.repair()

        assert repaired is True
        assert db.exists()
        todos = storage.load()
        assert len(todos) == 0


class TestRepairCLIIntegration:
    """Tests for repair command CLI integration."""

    def test_repair_command_exists_via_cli(self, tmp_path, monkeypatch) -> None:
        """Test 'todo repair' command is available."""
        from flywheel.cli import build_parser

        parser = build_parser()

        # Create corrupted file
        db = tmp_path / "corrupted.json"
        db.write_text('[{"id": 1, "text": "todo"},]')

        # Parse repair command (--db comes before subcommand)
        args = parser.parse_args(["--db", str(db), "repair"])

        assert args.command == "repair"
        assert args.db == str(db)

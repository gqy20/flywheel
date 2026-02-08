"""Tests for issue #2073: JSON file validation and repair methods.

This test suite verifies that TodoStorage can validate and repair corrupted JSON files.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoStorageValidate:
    """Tests for TodoStorage.validate() method."""

    def test_validate_returns_true_for_valid_json(self, tmp_path) -> None:
        """Test that validate returns True for a valid JSON file."""
        db = tmp_path / "valid.json"
        storage = TodoStorage(str(db))

        # Create valid JSON file
        todos = [Todo(id=1, text="valid todo")]
        storage.save(todos)

        # Validate should return True with no error
        is_valid, error = storage.validate()
        assert is_valid is True
        assert error is None

    def test_validate_returns_true_for_empty_file(self, tmp_path) -> None:
        """Test that validate returns True for a non-existent file (empty state)."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # Non-existent file is considered valid (will return empty list)
        is_valid, error = storage.validate()
        assert is_valid is True
        assert error is None

    def test_validate_returns_false_for_truncated_json(self, tmp_path) -> None:
        """Test that validate returns False with useful error for truncated JSON."""
        db = tmp_path / "truncated.json"
        storage = TodoStorage(str(db))

        # Create truncated JSON file
        db.write_text('[{"id": 1, "text": "task"}, {"id": 2, "text": "incomplete"')

        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None
        assert "json" in error.lower() or "parse" in error.lower()

    def test_validate_returns_false_for_invalid_json_type(self, tmp_path) -> None:
        """Test that validate returns False when JSON is not a list."""
        db = tmp_path / "invalid_type.json"
        storage = TodoStorage(str(db))

        # Create JSON that is not a list
        db.write_text('{"id": 1, "text": "not a list"}')

        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None
        assert "list" in error.lower()

    def test_validate_returns_false_for_malformed_json(self, tmp_path) -> None:
        """Test that validate returns False for malformed JSON."""
        db = tmp_path / "malformed.json"
        storage = TodoStorage(str(db))

        # Create malformed JSON (trailing comma)
        db.write_text('[{"id": 1, "text": "task"},]')

        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None


class TestTodoStorageRepair:
    """Tests for TodoStorage.repair() method."""

    def test_repair_creates_backup_before_repair(self, tmp_path) -> None:
        """Test that repair creates a .recovered.json backup."""
        db = tmp_path / "corrupt.json"
        storage = TodoStorage(str(db))

        # Create corrupted JSON
        db.write_text('[{"id": 1, "text": "task"},]')

        storage.repair()

        # Backup should be created
        backup = tmp_path / "corrupt.json.recovered.json"
        assert backup.exists()
        # Backup should contain original corrupted content
        assert backup.read_text() == '[{"id": 1, "text": "task"},]'

    def test_repair_extracts_valid_todos_from_trailing_comma(self, tmp_path) -> None:
        """Test that repair extracts valid todos from file with trailing comma."""
        db = tmp_path / "trailing_comma.json"
        storage = TodoStorage(str(db))

        # Create JSON with trailing comma (common error)
        db.write_text('[{"id": 1, "text": "first"}, {"id": 2, "text": "second"},]')

        repaired = storage.repair()

        # Should recover valid todos
        assert repaired >= 1  # At least one todo recovered
        # File should now be valid
        is_valid, _ = storage.validate()
        assert is_valid is True

    def test_repair_handles_truncated_json(self, tmp_path) -> None:
        """Test that repair handles truncated JSON gracefully."""
        db = tmp_path / "truncated.json"
        storage = TodoStorage(str(db))

        # Create truncated JSON
        db.write_text('[{"id": 1, "text": "complete"}, {"id": 2, "text": "inc')

        repaired = storage.repair()

        # Should recover at least the complete todo
        assert repaired >= 0
        # File should now be valid (possibly empty)
        is_valid, _ = storage.validate()
        assert is_valid is True

    def test_repair_handles_completely_invalid_json(self, tmp_path) -> None:
        """Test that repair handles completely invalid JSON gracefully."""
        db = tmp_path / "invalid.json"
        storage = TodoStorage(str(db))

        # Create completely invalid JSON
        db.write_text('this is not json at all {broken')

        repaired = storage.repair()

        # Should return 0 (no todos recovered)
        assert repaired == 0
        # File should now be valid (empty list)
        is_valid, _ = storage.validate()
        assert is_valid is True
        # File should contain empty list
        assert db.read_text() == "[]"

    def test_repair_handles_missing_fields(self, tmp_path) -> None:
        """Test that repair handles JSON objects with missing required fields."""
        db = tmp_path / "missing_fields.json"
        storage = TodoStorage(str(db))

        # Create JSON with objects missing required fields
        db.write_text(
            '[{"id": 1, "text": "valid"}, {"id": 2}, {"text": "no id"}, {"id": 3, "text": "also valid"}]'
        )

        repaired = storage.repair()

        # Should recover only valid todos (1 and 3)
        assert repaired == 2
        # Verify file contains valid todos
        todos = storage.load()
        assert len(todos) == 2
        assert todos[0].id == 1
        assert todos[0].text == "valid"
        assert todos[1].id == 3
        assert todos[1].text == "also valid"

    def test_repair_handles_valid_file_no_changes(self, tmp_path) -> None:
        """Test that repair doesn't change already valid files."""
        db = tmp_path / "valid.json"
        storage = TodoStorage(str(db))

        # Create valid JSON
        original_todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
        storage.save(original_todos)
        original_content = db.read_text()

        repaired = storage.repair()

        # Should return number of todos found
        assert repaired == 2
        # Content should be unchanged
        assert db.read_text() == original_content
        # No backup should be created for valid files
        backup = tmp_path / "valid.json.recovered.json"
        assert not backup.exists()

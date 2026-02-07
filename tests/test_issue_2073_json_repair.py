"""Regression test for issue #2073: File validation and repair for corrupted JSON.

This test suite verifies the validate() and repair() methods that provide
a recovery path when JSON files get corrupted (disk errors, concurrent writes,
manual edits), instead of cryptic JSONDecodeError.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoStorageValidation:
    """Tests for TodoStorage.validate() method."""

    def test_validate_returns_true_for_valid_json(self, tmp_path) -> None:
        """Test validate() returns True for valid JSON file."""
        db = tmp_path / "valid.json"
        storage = TodoStorage(str(db))

        # Create valid JSON file
        todos = [Todo(id=1, text="valid todo"), Todo(id=2, text="another todo")]
        storage.save(todos)

        # Validate should return True with no error
        is_valid, error = storage.validate()
        assert is_valid is True
        assert error is None

    def test_validate_returns_false_for_truncated_json(self, tmp_path) -> None:
        """Test validate() returns False with useful error for truncated JSON."""
        db = tmp_path / "truncated.json"
        storage = TodoStorage(str(db))

        # Create truncated JSON (missing closing bracket)
        db.write_text('["id": 1, "text": "incomplete"', encoding="utf-8")

        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None
        assert "line" in error.lower() or "column" in error.lower()

    def test_validate_returns_false_for_invalid_json(self, tmp_path) -> None:
        """Test validate() returns False for completely invalid JSON."""
        db = tmp_path / "invalid.json"
        storage = TodoStorage(str(db))

        # Create completely invalid JSON
        db.write_text("{not valid json at all}", encoding="utf-8")

        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None

    def test_validate_returns_false_for_trailing_comma(self, tmp_path) -> None:
        """Test validate() returns False for JSON with trailing comma."""
        db = tmp_path / "trailing_comma.json"
        storage = TodoStorage(str(db))

        # JSON with trailing comma is not valid
        db.write_text('[{"id": 1, "text": "todo"},]', encoding="utf-8")

        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None

    def test_validate_returns_true_for_nonexistent_file(self, tmp_path) -> None:
        """Test validate() returns True for nonexistent file (empty state is valid)."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # Nonexistent file should be considered valid (empty state)
        is_valid, error = storage.validate()
        assert is_valid is True
        assert error is None


class TestTodoStorageRepair:
    """Tests for TodoStorage.repair() method."""

    def test_repair_handles_valid_json(self, tmp_path) -> None:
        """Test repair() on valid JSON returns all todos."""
        db = tmp_path / "valid.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="todo1"), Todo(id=2, text="todo2")]
        storage.save(todos)

        # Create backup before repair
        backup = tmp_path / "valid.json.recovered.json"

        recovered = storage.repair(backup_path=str(backup))

        assert len(recovered) == 2
        assert recovered[0].text == "todo1"
        assert recovered[1].text == "todo2"
        # Backup should be created
        assert backup.exists()

    def test_repair_extracts_valid_from_trailing_comma(self, tmp_path) -> None:
        """Test repair() extracts valid todos from file with trailing comma."""
        db = tmp_path / "trailing.json"
        storage = TodoStorage(str(db))

        # Write JSON with trailing comma
        db.write_text('[{"id": 1, "text": "valid1"}, {"id": 2, "text": "valid2"},]', encoding="utf-8")

        backup = tmp_path / "trailing.json.recovered.json"
        recovered = storage.repair(backup_path=str(backup))

        # Should extract the valid todos
        assert len(recovered) == 2
        assert recovered[0].text == "valid1"
        assert recovered[1].text == "valid2"

    def test_repair_handles_completely_invalid_json(self, tmp_path) -> None:
        """Test repair() handles completely invalid JSON gracefully."""
        db = tmp_path / "invalid.json"
        storage = TodoStorage(str(db))

        # Write completely invalid content
        db.write_text('this is not json at all!!!', encoding="utf-8")

        backup = tmp_path / "invalid.json.recovered.json"
        recovered = storage.repair(backup_path=str(backup))

        # Should return empty list
        assert recovered == []

    def test_repair_creates_backup_before_fixing(self, tmp_path) -> None:
        """Test that repair() creates .recovered.json backup before attempting repairs."""
        db = tmp_path / "corrupt.json"
        storage = TodoStorage(str(db))

        # Create corrupted file
        corrupted_content = '[{"id": 1, "text": "partial"}'
        db.write_text(corrupted_content, encoding="utf-8")

        backup = tmp_path / "corrupt.json.recovered.json"
        storage.repair(backup_path=str(backup))

        # Backup should contain original corrupted content
        assert backup.exists()
        backup_content = backup.read_text(encoding="utf-8")
        assert backup_content == corrupted_content

    def test_repair_saves_recovered_data(self, tmp_path) -> None:
        """Test that repair() saves recovered data to the file."""
        db = tmp_path / "repairable.json"
        storage = TodoStorage(str(db))

        # Write repairable JSON (trailing comma)
        db.write_text('[{"id": 1, "text": "recovered"},]', encoding="utf-8")

        backup = tmp_path / "repairable.json.recovered.json"
        storage.repair(backup_path=str(backup))

        # After repair, file should contain valid JSON
        reloaded = storage.load()
        assert len(reloaded) == 1
        assert reloaded[0].text == "recovered"

"""Tests for JSON validation and repair functionality.

This test suite verifies the validate() and repair() methods that provide
recovery paths when JSON files get corrupted (disk errors, concurrent writes, manual edits).

Issue: https://github.com/gqy20/flywheel/issues/2073
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoStorageValidate:
    """Test suite for TodoStorage.validate() method."""

    def test_validate_returns_true_for_valid_json(self, tmp_path) -> None:
        """Test that validate() returns (True, None) for a valid JSON file."""
        db = tmp_path / "valid.json"
        storage = TodoStorage(str(db))

        # Create a valid todo file
        todos = [Todo(id=1, text="Task 1"), Todo(id=2, text="Task 2")]
        storage.save(todos)

        # Validate should pass
        is_valid, error = storage.validate()
        assert is_valid is True
        assert error is None

    def test_validate_returns_true_for_empty_file(self, tmp_path) -> None:
        """Test that validate() returns (True, None) for a non-existent file."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # Non-existent file is valid (will return empty list on load)
        is_valid, error = storage.validate()
        assert is_valid is True
        assert error is None

    def test_validate_returns_false_for_truncated_json(self, tmp_path) -> None:
        """Test that validate() returns False with useful error for truncated JSON."""
        db = tmp_path / "truncated.json"
        storage = TodoStorage(str(db))

        # Create truncated JSON file
        db.write_text('[{"id": 1, "text": "Task 1"}, {"id": 2, "text": "Task 2"')

        # Validate should fail with descriptive error
        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None
        # Error message should mention JSON or parsing issues
        assert "json" in error.lower() or "parse" in error.lower() or "incomplete" in error.lower()

    def test_validate_returns_false_for_invalid_json(self, tmp_path) -> None:
        """Test that validate() returns False for completely invalid JSON."""
        db = tmp_path / "invalid.json"
        storage = TodoStorage(str(db))

        # Create completely invalid file
        db.write_text("This is not JSON at all!!!")

        # Validate should fail
        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None

    def test_validate_returns_false_for_trailing_comma(self, tmp_path) -> None:
        """Test that validate() returns False for JSON with trailing comma."""
        db = tmp_path / "trailing_comma.json"
        storage = TodoStorage(str(db))

        # Create JSON with trailing comma (common manual edit error)
        db.write_text('[{"id": 1, "text": "Task 1"},]')

        # Validate should fail
        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None

    def test_validate_returns_false_for_non_list_json(self, tmp_path) -> None:
        """Test that validate() returns False when JSON is not a list."""
        db = tmp_path / "not_list.json"
        storage = TodoStorage(str(db))

        # Create valid JSON but wrong structure (object instead of list)
        db.write_text('{"todos": []}')

        # Validate should fail
        is_valid, error = storage.validate()
        assert is_valid is False
        assert error is not None
        assert "list" in error.lower()


class TestTodoStorageRepair:
    """Test suite for TodoStorage.repair() method."""

    def test_repair_creates_backup_before_repair(self, tmp_path) -> None:
        """Test that repair() creates .recovered.json backup before attempting repairs."""
        db = tmp_path / "corrupted.json"
        storage = TodoStorage(str(db))

        # Create corrupted file
        corrupted_content = '[{"id": 1, "text": "Task 1"}, {"id": 2, "text": "Task 2"'
        db.write_text(corrupted_content)

        # Repair should create backup
        storage.repair()

        backup_path = tmp_path / "corrupted.json.recovered.json"
        assert backup_path.exists()
        # Backup should contain original corrupted content
        assert backup_path.read_text(encoding="utf-8") == corrupted_content

    def test_repair_extracts_valid_todos_from_trailing_comma(self, tmp_path) -> None:
        """Test that repair() extracts valid todos from file with trailing comma."""
        db = tmp_path / "trailing_comma.json"
        storage = TodoStorage(str(db))

        # Create JSON with trailing comma
        db.write_text('[{"id": 1, "text": "Task 1"}, {"id": 2, "text": "Task 2"},]')

        # Repair should extract valid todos
        recovered = storage.repair()

        assert recovered is True
        # Verify file is now valid and contains the todos
        todos = storage.load()
        assert len(todos) == 2
        assert todos[0].id == 1
        assert todos[0].text == "Task 1"
        assert todos[1].id == 2
        assert todos[1].text == "Task 2"

    def test_repair_handles_truncated_json(self, tmp_path) -> None:
        """Test that repair() handles truncated JSON gracefully."""
        db = tmp_path / "truncated.json"
        storage = TodoStorage(str(db))

        # Create truncated JSON file
        db.write_text('[{"id": 1, "text": "Task 1"}, {"id": 2, "text": "Task 2"')

        # Repair should attempt to extract valid todos
        storage.repair()

        # Should recover at least the first complete todo object
        todos = storage.load()
        assert len(todos) >= 1
        assert todos[0].id == 1
        assert todos[0].text == "Task 1"

    def test_repair_handles_completely_invalid_json(self, tmp_path) -> None:
        """Test that repair() handles completely invalid JSON gracefully."""
        db = tmp_path / "invalid.json"
        storage = TodoStorage(str(db))

        # Create completely invalid file
        db.write_text("This is not JSON at all!!!")

        # Repair should return False and not crash
        recovered = storage.repair()

        assert recovered is False
        # File should still exist (or be replaced with empty list)
        assert db.exists()

    def test_repair_preserves_valid_todos_from_partially_corrupted_file(
        self, tmp_path
    ) -> None:
        """Test that repair() preserves valid todos from partially corrupted file."""
        db = tmp_path / "partial.json"
        storage = TodoStorage(str(db))

        # Create file with multiple valid todos followed by corruption
        # This simulates a write that was interrupted
        valid_content = json.dumps(
            [
                {"id": 1, "text": "Task 1", "done": False},
                {"id": 2, "text": "Task 2", "done": True},
                {"id": 3, "text": "Task 3", "done": False},
            ],
            indent=2,
        )
        # Truncate in the middle of the third todo
        corrupted_content = valid_content[: len(valid_content) - 20]
        db.write_text(corrupted_content)

        # Repair should recover the first 2 valid todos
        storage.repair()

        todos = storage.load()
        # Should have at least 2 complete todos
        assert len(todos) >= 2

    def test_repair_does_not_modify_valid_file(self, tmp_path) -> None:
        """Test that repair() does not modify a valid JSON file."""
        db = tmp_path / "valid.json"
        storage = TodoStorage(str(db))

        # Create valid file
        original_todos = [Todo(id=1, text="Task 1"), Todo(id=2, text="Task 2")]
        storage.save(original_todos)
        original_content = db.read_text(encoding="utf-8")

        # Repair should succeed without changes
        recovered = storage.repair()

        assert recovered is True
        # Content should be identical
        assert db.read_text(encoding="utf-8") == original_content

        # No backup should be created for valid files
        backup_path = tmp_path / "valid.json.recovered.json"
        assert not backup_path.exists()

    def test_repair_returns_false_for_nonexistent_file(self, tmp_path) -> None:
        """Test that repair() returns False for non-existent file."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        # Repair should return False (nothing to repair)
        recovered = storage.repair()

        assert recovered is False

"""Tests for JSON validation and repair methods (Issue #2073).

These tests verify that:
1. validate() method returns (is_valid: bool, error_message: str | None)
2. repair() method attempts to recover valid todos from corrupted JSON
3. repair() creates .recovered.json backup before attempting repairs
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_validate_returns_true_for_valid_json(tmp_path) -> None:
    """validate() should return (True, None) for valid JSON file."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    storage.save([Todo(id=1, text="task1"), Todo(id=2, text="task2")])

    # Validate should return (True, None)
    is_valid, error = storage.validate()
    assert is_valid is True
    assert error is None


def test_validate_returns_false_for_truncated_json(tmp_path) -> None:
    """validate() should return (False, error_message) for truncated JSON."""
    db = tmp_path / "truncated.json"
    storage = TodoStorage(str(db))

    # Create a truncated JSON file (missing closing bracket)
    db.write_text('[{"id": 1, "text": "task1"}', encoding="utf-8")

    # Validate should return (False, error_message)
    is_valid, error = storage.validate()
    assert is_valid is False
    assert error is not None
    assert "json" in error.lower() or "parse" in error.lower()


def test_validate_returns_false_for_completely_invalid_json(tmp_path) -> None:
    """validate() should return (False, error_message) for completely invalid JSON."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Create a completely invalid JSON file
    db.write_text("not json at all", encoding="utf-8")

    # Validate should return (False, error_message)
    is_valid, error = storage.validate()
    assert is_valid is False
    assert error is not None
    assert "json" in error.lower() or "parse" in error.lower()


def test_validate_returns_false_for_trailing_comma(tmp_path) -> None:
    """validate() should return (False, error_message) for JSON with trailing comma."""
    db = tmp_path / "trailing_comma.json"
    storage = TodoStorage(str(db))

    # Create JSON with trailing comma (common error from manual edits)
    db.write_text('[{"id": 1, "text": "task1"},]', encoding="utf-8")

    # Validate should return (False, error_message)
    is_valid, error = storage.validate()
    assert is_valid is False
    assert error is not None


def test_validate_returns_false_for_nonexistent_file(tmp_path) -> None:
    """validate() should return (False, error_message) for nonexistent file."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Validate should return (False, error_message) for missing file
    is_valid, error = storage.validate()
    assert is_valid is False
    assert error is not None
    assert "not found" in error.lower() or "no such" in error.lower()


def test_repair_extracts_valid_todos_from_trailing_comma(tmp_path) -> None:
    """repair() should extract valid todos from file with trailing comma."""
    db = tmp_path / "trailing_comma.json"
    storage = TodoStorage(str(db))

    # Create JSON with trailing comma
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"},]', encoding="utf-8")

    # Repair should recover the todos
    repaired = storage.repair()
    assert len(repaired) >= 1  # Should recover at least the first todo
    assert any(t.text == "task1" for t in repaired)

    # Original file should now be valid JSON
    is_valid, error = storage.validate()
    assert is_valid, f"After repair, file should be valid but got: {error}"


def test_repair_creates_backup_before_repair(tmp_path) -> None:
    """repair() should create .recovered.json backup before attempting repairs."""
    db = tmp_path / "corrupt.json"
    storage = TodoStorage(str(db))

    # Create corrupted JSON
    corrupted_content = '[{"id": 1, "text": "task1"},'
    db.write_text(corrupted_content, encoding="utf-8")

    # Repair should create backup
    storage.repair()

    # Backup file should exist
    backup_path = tmp_path / "corrupt.json.recovered"
    assert backup_path.exists()
    # Backup should contain original corrupted content
    assert backup_path.read_text(encoding="utf-8") == corrupted_content


def test_repair_handles_completely_invalid_json_gracefully(tmp_path) -> None:
    """repair() should handle completely invalid JSON gracefully."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Create completely invalid JSON
    db.write_text("this is not json at all {{{", encoding="utf-8")

    # Repair should not crash, should return empty list or partial recovery
    repaired = storage.repair()
    assert isinstance(repaired, list)

    # Should still create backup
    backup_path = tmp_path / "invalid.json.recovered"
    assert backup_path.exists()


def test_repair_handles_empty_file_gracefully(tmp_path) -> None:
    """repair() should handle empty file gracefully."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Create empty file
    db.write_text("", encoding="utf-8")

    # Repair should return empty list
    repaired = storage.repair()
    assert repaired == []

    # File should now contain valid JSON (empty array)
    is_valid, _ = storage.validate()
    assert is_valid


def test_repair_handles_truncated_json_with_partial_objects(tmp_path) -> None:
    """repair() should extract complete objects from truncated JSON."""
    db = tmp_path / "truncated.json"
    storage = TodoStorage(str(db))

    # Create truncated JSON with partial last object
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "ta', encoding="utf-8")

    # Repair should recover complete objects
    repaired = storage.repair()
    assert len(repaired) >= 1
    assert repaired[0].text == "task1"


def test_repair_with_nonexistent_file_creates_empty_valid_json(tmp_path) -> None:
    """repair() with nonexistent file should create empty valid JSON."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist
    assert not db.exists()

    # Repair should create empty valid JSON
    repaired = storage.repair()
    assert repaired == []

    # File should now exist and be valid
    assert db.exists()
    is_valid, _ = storage.validate()
    assert is_valid

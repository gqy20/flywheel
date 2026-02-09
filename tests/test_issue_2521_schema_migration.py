"""Tests for schema version validation and migration support in TodoStorage.

This test suite verifies that TodoStorage properly handles schema versioning,
including validation of version fields and support for future migrations.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_with_matching_version_succeeds(tmp_path) -> None:
    """Test that loading data with matching schema version succeeds."""
    db = tmp_path / "todo.json"

    # Create a valid JSON file with current schema version
    data = {
        "_version": 1,
        "todos": [
            {"id": 1, "text": "task 1", "done": False, "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"}
        ]
    }
    db.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    storage = TodoStorage(str(db))
    loaded = storage.load()

    assert len(loaded) == 1
    assert loaded[0].text == "task 1"


def test_load_with_missing_version_fails_with_clear_error(tmp_path) -> None:
    """Test that loading data without _version field fails with clear error."""
    db = tmp_path / "todo.json"

    # Create JSON file without version field (old format)
    data = [
        {"id": 1, "text": "task 1", "done": False, "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"}
    ]
    db.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    storage = TodoStorage(str(db))

    with pytest.raises(ValueError, match=r"Schema version.*missing.*outdated"):
        storage.load()


def test_load_with_future_version_fails_with_clear_error(tmp_path) -> None:
    """Test that loading data with future version fails with clear error."""
    db = tmp_path / "todo.json"

    # Create JSON file with future schema version
    data = {
        "_version": 999,
        "todos": [
            {"id": 1, "text": "task 1", "done": False, "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"}
        ]
    }
    db.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    storage = TodoStorage(str(db))

    with pytest.raises(ValueError, match=r"Schema version.*999.*newer than supported.*1"):
        storage.load()


def test_save_includes_version_in_output_json(tmp_path) -> None:
    """Test that saved JSON includes _version field."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test task")]
    storage.save(todos)

    # Verify the saved JSON contains _version
    raw_content = db.read_text(encoding="utf-8")
    parsed = json.loads(raw_content)

    assert "_version" in parsed
    assert parsed["_version"] == 1
    assert "todos" in parsed


def test_save_maintains_existing_json_structure(tmp_path) -> None:
    """Test that saved JSON has correct structure with todos array."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="task 1", done=True),
        Todo(id=2, text="task 2"),
    ]
    storage.save(todos)

    # Verify the saved JSON structure
    raw_content = db.read_text(encoding="utf-8")
    parsed = json.loads(raw_content)

    assert parsed["_version"] == 1
    assert isinstance(parsed["todos"], list)
    assert len(parsed["todos"]) == 2
    assert parsed["todos"][0]["text"] == "task 1"
    assert parsed["todos"][1]["text"] == "task 2"


def test_load_empty_file_returns_empty_list(tmp_path) -> None:
    """Test that loading from non-existent file returns empty list."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    loaded = storage.load()
    assert loaded == []


def test_version_check_happens_before_json_list_validation(tmp_path) -> None:
    """Test that version validation occurs before list structure validation."""
    db = tmp_path / "todo.json"

    # Create invalid structure without version
    # This should raise version error, not "must be a list" error
    invalid_data = {"invalid": "structure", "without": "version"}
    db.write_text(json.dumps(invalid_data, ensure_ascii=False), encoding="utf-8")

    storage = TodoStorage(str(db))

    # Should complain about missing version, not about not being a list
    with pytest.raises(ValueError, match=r"Schema version.*missing"):
        storage.load()

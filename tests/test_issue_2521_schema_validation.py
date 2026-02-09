"""Tests for schema version validation (Issue #2521).

These tests verify that:
1. JSON files include a '_version' key with current schema version
2. TodoStorage.load() raises clear error when version mismatch is detected
3. A migration registry exists (can be empty initially)
4. Existing tests pass and new version validation tests are added
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_with_matching_version_succeeds(tmp_path) -> None:
    """Loading JSON with matching _version should succeed."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file with version 1
    data = {
        "_version": 1,
        "todos": [
            {"id": 1, "text": "task1", "done": False, "created_at": "", "updated_at": ""},
            {"id": 2, "text": "task2", "done": True, "created_at": "", "updated_at": ""},
        ],
    }
    db.write_text(json.dumps(data), encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].text == "task1"
    assert todos[1].text == "task2"


def test_load_with_missing_version_fails(tmp_path) -> None:
    """JSON without _version field should raise clear error."""
    db = tmp_path / "no_version.json"
    storage = TodoStorage(str(db))

    # Create JSON without _version field (legacy format)
    legacy_data = [
        {"id": 1, "text": "task1", "done": False},
        {"id": 2, "text": "task2", "done": True},
    ]
    db.write_text(json.dumps(legacy_data), encoding="utf-8")

    # Should raise ValueError with clear message about missing version
    with pytest.raises(ValueError, match=r"missing.*'_version'|version.*required|schema.*version"):
        storage.load()


def test_load_with_dict_without_version_key_fails(tmp_path) -> None:
    """JSON dict without _version field should raise clear error."""
    db = tmp_path / "no_version_dict.json"
    storage = TodoStorage(str(db))

    # Create JSON dict without _version field
    data = {"todos": [{"id": 1, "text": "task1", "done": False}]}
    db.write_text(json.dumps(data), encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"missing.*'_version'|'_version'|corrupted"):
        storage.load()


def test_load_with_future_version_fails(tmp_path) -> None:
    """JSON with future version should raise clear error message."""
    db = tmp_path / "future_version.json"
    storage = TodoStorage(str(db))

    # Create JSON with future version (e.g., from newer app version)
    data = {
        "_version": 999,
        "todos": [{"id": 1, "text": "task1", "done": False}],
    }
    db.write_text(json.dumps(data), encoding="utf-8")

    # Should raise ValueError with clear message about version mismatch
    with pytest.raises(ValueError, match=r"version.*mismatch|unsupported.*version|upgrade.*required"):
        storage.load()


def test_save_includes_version(tmp_path) -> None:
    """Saving should include _version in output JSON."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="task1"),
        Todo(id=2, text="task2", done=True),
    ]

    storage.save(todos)

    # Verify the saved JSON contains _version
    raw_content = db.read_text(encoding="utf-8")
    parsed = json.loads(raw_content)

    assert "_version" in parsed, "Saved JSON should include '_version' key"
    assert parsed["_version"] == 1, "Current schema version should be 1"
    assert "todos" in parsed, "Saved JSON should include 'todos' key"
    assert len(parsed["todos"]) == 2


def test_save_and_load_roundtrip(tmp_path) -> None:
    """Full roundtrip: save -> load -> verify data integrity."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_todos = [
        Todo(id=1, text="task with unicode: 你好"),
        Todo(id=2, text="task with quotes: \"test\"", done=True),
        Todo(id=3, text="task with \\n newline"),
    ]

    # Save
    storage.save(original_todos)

    # Load
    loaded_todos = storage.load()

    # Verify
    assert len(loaded_todos) == 3
    assert loaded_todos[0].text == "task with unicode: 你好"
    assert loaded_todos[1].text == 'task with quotes: "test"'
    assert loaded_todos[1].done is True
    assert loaded_todos[2].text == "task with \\n newline"


def test_load_with_zero_version_fails(tmp_path) -> None:
    """JSON with _version: 0 should be treated as invalid."""
    db = tmp_path / "zero_version.json"
    storage = TodoStorage(str(db))

    data = {
        "_version": 0,
        "todos": [{"id": 1, "text": "task1", "done": False}],
    }
    db.write_text(json.dumps(data), encoding="utf-8")

    # Should raise ValueError
    with pytest.raises(ValueError, match=r"version.*mismatch|invalid.*version|Version must be"):
        storage.load()


def test_load_with_negative_version_fails(tmp_path) -> None:
    """JSON with negative version should be treated as invalid."""
    db = tmp_path / "negative_version.json"
    storage = TodoStorage(str(db))

    data = {
        "_version": -1,
        "todos": [{"id": 1, "text": "task1", "done": False}],
    }
    db.write_text(json.dumps(data), encoding="utf-8")

    # Should raise ValueError
    with pytest.raises(ValueError, match=r"version.*mismatch|invalid.*version|Version must be"):
        storage.load()


def test_current_schema_version_constant() -> None:
    """Verify CURRENT_SCHEMA_VERSION constant exists and is valid."""
    from flywheel.storage import CURRENT_SCHEMA_VERSION

    assert isinstance(CURRENT_SCHEMA_VERSION, int)
    assert CURRENT_SCHEMA_VERSION >= 1

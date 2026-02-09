"""Tests for schema version validation and migration support (issue #2521).

This test suite verifies that TodoStorage validates schema versions and
handles data format changes gracefully.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import CURRENT_SCHEMA_VERSION, TodoStorage
from flywheel.todo import Todo


class TestSchemaVersionValidation:
    """Test schema version validation in TodoStorage."""

    def test_load_with_matching_version_succeeds(self, tmp_path) -> None:
        """Test that loading a file with matching version succeeds."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save a todo to create a versioned file
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # Verify the file contains the version field
        raw_content = json.loads(db.read_text(encoding="utf-8"))
        assert "_version" in raw_content
        assert raw_content["_version"] == CURRENT_SCHEMA_VERSION

        # Loading should succeed
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"

    def test_load_with_missing_version_fails_with_clear_error(self, tmp_path) -> None:
        """Test that loading a file without version field fails with clear error."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a file without version field (old format)
        old_format_data = [
            {"id": 1, "text": "old todo", "done": False, "created_at": "", "updated_at": ""}
        ]
        db.write_text(json.dumps(old_format_data), encoding="utf-8")

        # Loading should fail with a clear error message
        with pytest.raises(ValueError, match=r"Schema version is missing.*upgrade your data"):
            storage.load()

    def test_load_with_future_version_fails_with_clear_error(self, tmp_path) -> None:
        """Test that loading a file with future version fails with clear error message."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create a file with a future version
        future_version = CURRENT_SCHEMA_VERSION + 1
        future_format_data = {
            "_version": future_version,
            "todos": [
                {"id": 1, "text": "future todo", "done": False, "created_at": "", "updated_at": ""}
            ],
        }
        db.write_text(json.dumps(future_format_data), encoding="utf-8")

        # Loading should fail with a clear error message about version mismatch
        with pytest.raises(ValueError, match=r"Schema version mismatch.*version 2.*expects version 1"):
            storage.load()

    def test_save_includes_version_in_output_json(self, tmp_path) -> None:
        """Test that save includes version field in output JSON."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="task 1", done=True),
            Todo(id=2, text="task 2"),
        ]
        storage.save(todos)

        # Verify the saved JSON contains the version field
        raw_content = json.loads(db.read_text(encoding="utf-8"))
        assert "_version" in raw_content
        assert raw_content["_version"] == CURRENT_SCHEMA_VERSION

        # Verify todos are still accessible
        assert "todos" in raw_content
        assert len(raw_content["todos"]) == 2

    def test_load_empty_file_returns_empty_list(self, tmp_path) -> None:
        """Test that loading a non-existent file returns empty list."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        loaded = storage.load()
        assert loaded == []

    def test_schema_version_constant_exists(self) -> None:
        """Test that CURRENT_SCHEMA_VERSION constant is defined."""
        assert isinstance(CURRENT_SCHEMA_VERSION, int)
        assert CURRENT_SCHEMA_VERSION > 0

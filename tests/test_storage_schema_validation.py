"""Tests for JSON schema validation in TodoStorage.load().

This test suite verifies that TodoStorage properly validates the schema
of loaded JSON data to prevent injection of malformed data.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


class TestJSONSchemaValidation:
    """Test JSON schema validation on load."""

    def test_load_with_non_list_root_raises_clear_error(self, tmp_path) -> None:
        """Test that JSON with non-list root raises a clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text('{"not": "a list"}', encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="Todo storage must be a JSON list"):
            storage.load()

    def test_load_with_dict_root_raises_clear_error(self, tmp_path) -> None:
        """Test that JSON dict root raises a clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text('{"root": "dict"}', encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="Todo storage must be a JSON list"):
            storage.load()

    def test_load_with_string_root_raises_clear_error(self, tmp_path) -> None:
        """Test that JSON string root raises a clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text('"just a string"', encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="Todo storage must be a JSON list"):
            storage.load()

    def test_load_with_number_root_raises_clear_error(self, tmp_path) -> None:
        """Test that JSON number root raises a clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text("42", encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="Todo storage must be a JSON list"):
            storage.load()

    def test_load_with_item_missing_id_raises_clear_error(self, tmp_path) -> None:
        """Test that list item missing 'id' field raises clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text('[{"text": "no id"}]', encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match=r"missing required field.*'id'"):
            storage.load()

    def test_load_with_item_missing_text_raises_clear_error(self, tmp_path) -> None:
        """Test that list item missing 'text' field raises clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text('[{"id": 1}]', encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match=r"missing required field.*'text'"):
            storage.load()

    def test_load_with_item_missing_both_required_fields_raises_clear_error(self, tmp_path) -> None:
        """Test that list item missing both 'id' and 'text' raises clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text('[{"done": true}]', encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="missing required field"):
            storage.load()

    def test_load_with_string_id_raises_clear_error(self, tmp_path) -> None:
        """Test that item with string 'id' instead of int raises clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text('[{"id": "not-an-int", "text": "test"}]', encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="field 'id' must be an int"):
            storage.load()

    def test_load_with_non_string_text_raises_clear_error(self, tmp_path) -> None:
        """Test that item with non-string 'text' raises clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text('[{"id": 1, "text": 123}]', encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="field 'text' must be a string"):
            storage.load()

    def test_load_with_non_bool_done_raises_clear_error(self, tmp_path) -> None:
        """Test that item with non-bool 'done' raises clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text('[{"id": 1, "text": "test", "done": "yes"}]', encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="field 'done' must be a bool"):
            storage.load()

    def test_load_with_valid_data_succeeds(self, tmp_path) -> None:
        """Test that valid JSON data loads successfully."""
        db = tmp_path / "todo.json"
        valid_data = [
            {"id": 1, "text": "first task", "done": False},
            {"id": 2, "text": "second task", "done": True},
        ]
        db.write_text(json.dumps(valid_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        todos = storage.load()

        assert len(todos) == 2
        assert todos[0].id == 1
        assert todos[0].text == "first task"
        assert todos[0].done is False
        assert todos[1].id == 2
        assert todos[1].text == "second task"
        assert todos[1].done is True

    def test_load_with_optional_fields_omitted_succeeds(self, tmp_path) -> None:
        """Test that items with only required fields load successfully."""
        db = tmp_path / "todo.json"
        db.write_text('[{"id": 1, "text": "minimal todo"}]', encoding="utf-8")

        storage = TodoStorage(str(db))
        todos = storage.load()

        assert len(todos) == 1
        assert todos[0].id == 1
        assert todos[0].text == "minimal todo"
        assert todos[0].done is False  # default value

    def test_load_with_extra_unknown_fields_succeeds(self, tmp_path) -> None:
        """Test that items with extra fields load successfully (forward compatibility)."""
        db = tmp_path / "todo.json"
        db.write_text(
            '[{"id": 1, "text": "test", "extra_field": "ignored", "another": 42}]',
            encoding="utf-8",
        )

        storage = TodoStorage(str(db))
        todos = storage.load()

        assert len(todos) == 1
        assert todos[0].id == 1
        assert todos[0].text == "test"

    def test_load_with_non_dict_item_raises_clear_error(self, tmp_path) -> None:
        """Test that list containing non-dict items raises clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text("[1, 2, 3]", encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="item at index 0 must be a JSON object"):
            storage.load()

    def test_load_with_mixed_valid_invalid_items_raises_clear_error(self, tmp_path) -> None:
        """Test that list with one invalid item raises clear error at that position."""
        db = tmp_path / "todo.json"
        db.write_text(
            '[{"id": 1, "text": "valid"}, {"text": "no id"}]',
            encoding="utf-8",
        )

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match=r"item at index 1.*missing required field"):
            storage.load()

    def test_load_with_empty_list_succeeds(self, tmp_path) -> None:
        """Test that empty list loads successfully."""
        db = tmp_path / "todo.json"
        db.write_text("[]", encoding="utf-8")

        storage = TodoStorage(str(db))
        todos = storage.load()

        assert todos == []

    def test_load_with_null_in_list_raises_clear_error(self, tmp_path) -> None:
        """Test that list containing null raises clear ValueError."""
        db = tmp_path / "todo.json"
        db.write_text('[null, {"id": 1, "text": "test"}]', encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match=r"item at index 0.*must be a JSON object"):
            storage.load()

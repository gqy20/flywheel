"""Tests for JSON schema validation in TodoStorage.load().

This test suite verifies that TodoStorage.load() properly validates
incoming JSON data structure to prevent malformed data injection attacks
as described in issue #1923.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


class TestLoadValidatesRequiredFields:
    """Tests that load() validates presence of required fields."""

    def test_load_raises_value_error_for_item_missing_id(self, tmp_path) -> None:
        """Test that items without 'id' field raise ValueError."""
        db = tmp_path / "todo.json"
        malformed_data = [{"text": "task without id"}]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="required field 'id'"):
            storage.load()

    def test_load_raises_value_error_for_item_missing_text(self, tmp_path) -> None:
        """Test that items without 'text' field raise ValueError."""
        db = tmp_path / "todo.json"
        malformed_data = [{"id": 1}]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="required field 'text'"):
            storage.load()

    def test_load_raises_value_error_for_item_missing_both_fields(
        self, tmp_path
    ) -> None:
        """Test that items with neither 'id' nor 'text' raise ValueError."""
        db = tmp_path / "todo.json"
        malformed_data = [{"done": True}]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="required field"):
            storage.load()

    def test_load_raises_value_error_for_empty_dict_item(self, tmp_path) -> None:
        """Test that empty dict items raise ValueError."""
        db = tmp_path / "todo.json"
        malformed_data = [{}]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="required field"):
            storage.load()


class TestLoadValidatesFieldTypes:
    """Tests that load() validates correct types for fields."""

    def test_load_raises_value_error_for_id_as_string(self, tmp_path) -> None:
        """Test that 'id' as string instead of int raises ValueError."""
        db = tmp_path / "todo.json"
        malformed_data = [{"id": "not-an-int", "text": "task"}]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="'id' must be an integer"):
            storage.load()

    def test_load_raises_value_error_for_id_as_float(self, tmp_path) -> None:
        """Test that 'id' as float raises ValueError."""
        db = tmp_path / "todo.json"
        malformed_data = [{"id": 1.5, "text": "task"}]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="'id' must be an integer"):
            storage.load()

    def test_load_raises_value_error_for_text_as_int(self, tmp_path) -> None:
        """Test that 'text' as int instead of string raises ValueError."""
        db = tmp_path / "todo.json"
        malformed_data = [{"id": 1, "text": 123}]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="'text' must be a string"):
            storage.load()

    def test_load_raises_value_error_for_done_as_string(self, tmp_path) -> None:
        """Test that 'done' as string instead of bool raises ValueError."""
        db = tmp_path / "todo.json"
        malformed_data = [{"id": 1, "text": "task", "done": "true"}]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="'done' must be a boolean"):
            storage.load()

    def test_load_raises_value_error_for_done_as_int(self, tmp_path) -> None:
        """Test that 'done' as int instead of bool raises ValueError."""
        db = tmp_path / "todo.json"
        malformed_data = [{"id": 1, "text": "task", "done": 1}]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="'done' must be a boolean"):
            storage.load()


class TestLoadHandlesExtraFields:
    """Tests that load() handles extra fields gracefully."""

    def test_load_ignores_extra_unknown_fields(self, tmp_path) -> None:
        """Test that extra unknown fields are ignored (not an error)."""
        db = tmp_path / "todo.json"
        data_with_extra = [
            {
                "id": 1,
                "text": "task",
                "done": False,
                "unknown_field": "should be ignored",
                "malicious_payload": "should not cause crash",
            }
        ]
        db.write_text(json.dumps(data_with_extra), encoding="utf-8")

        storage = TodoStorage(str(db))
        loaded = storage.load()

        assert len(loaded) == 1
        assert loaded[0].id == 1
        assert loaded[0].text == "task"
        assert loaded[0].done is False
        # Extra fields should not be present on the Todo object
        assert not hasattr(loaded[0], "unknown_field")


class TestLoadValidatesItemStructure:
    """Tests that load() validates each item is a dict."""

    def test_load_raises_value_error_for_non_dict_items(self, tmp_path) -> None:
        """Test that non-dict items in the list raise ValueError."""
        db = tmp_path / "todo.json"
        malformed_data = ["string-instead-of-dict", 123, None]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="must be a JSON object"):
            storage.load()

    def test_load_raises_value_error_for_list_in_list(self, tmp_path) -> None:
        """Test that nested lists raise ValueError."""
        db = tmp_path / "todo.json"
        malformed_data = [[1, 2, 3]]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match="must be a JSON object"):
            storage.load()

    def test_load_raises_value_error_for_item_at_specific_index(
        self, tmp_path
    ) -> None:
        """Test that error message includes the index of the invalid item."""
        db = tmp_path / "todo.json"
        malformed_data = [
            {"id": 1, "text": "valid"},
            {"text": "missing id"},
            {"id": 2, "text": "also valid"},
        ]
        db.write_text(json.dumps(malformed_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        with pytest.raises(ValueError, match=r"index 1"):
            storage.load()


class TestLoadWithValidData:
    """Tests that load() still accepts valid data."""

    def test_load_accepts_minimal_valid_item(self, tmp_path) -> None:
        """Test that minimal valid item (id + text) loads successfully."""
        db = tmp_path / "todo.json"
        valid_data = [{"id": 1, "text": "minimal task"}]
        db.write_text(json.dumps(valid_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        loaded = storage.load()

        assert len(loaded) == 1
        assert loaded[0].id == 1
        assert loaded[0].text == "minimal task"
        assert loaded[0].done is False

    def test_load_accepts_full_valid_item(self, tmp_path) -> None:
        """Test that fully specified item loads successfully."""
        db = tmp_path / "todo.json"
        valid_data = [
            {
                "id": 1,
                "text": "full task",
                "done": True,
                "created_at": "2024-01-01T00:00:00+00:00",
                "updated_at": "2024-01-02T00:00:00+00:00",
            }
        ]
        db.write_text(json.dumps(valid_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        loaded = storage.load()

        assert len(loaded) == 1
        assert loaded[0].id == 1
        assert loaded[0].text == "full task"
        assert loaded[0].done is True
        assert loaded[0].created_at == "2024-01-01T00:00:00+00:00"

    def test_load_accepts_valid_bool_variants(self, tmp_path) -> None:
        """Test that valid boolean values work correctly."""
        db = tmp_path / "todo.json"
        valid_data = [
            {"id": 1, "text": "task1", "done": True},
            {"id": 2, "text": "task2", "done": False},
        ]
        db.write_text(json.dumps(valid_data), encoding="utf-8")

        storage = TodoStorage(str(db))
        loaded = storage.load()

        assert len(loaded) == 2
        assert loaded[0].done is True
        assert loaded[1].done is False


class TestLoadEmptyList:
    """Tests that load() handles empty list correctly."""

    def test_load_accepts_empty_list(self, tmp_path) -> None:
        """Test that empty JSON list loads successfully as empty todos."""
        db = tmp_path / "todo.json"
        db.write_text("[]", encoding="utf-8")

        storage = TodoStorage(str(db))
        loaded = storage.load()

        assert loaded == []

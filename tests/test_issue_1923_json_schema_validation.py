"""Tests for JSON schema validation at storage level (Issue #1923).

These tests verify that TodoStorage.load() validates the schema of JSON data
before passing it to Todo.from_dict(). This provides defense-in-depth security
by ensuring malformed data is caught early with clear error messages.

Acceptance criteria:
- Malformed JSON returns clear error message instead of unhandled exception
- Invalid field types (e.g., id as string) are caught at storage level
- Missing required fields produce actionable error messages
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


class TestStorageLoadSchemaValidation:
    """Schema validation tests for TodoStorage.load()."""

    def test_non_list_root_raises_clear_error(self, tmp_path) -> None:
        """JSON with non-list root should produce clear error message."""
        db = tmp_path / "not_a_list.json"
        storage = TodoStorage(str(db))

        # Valid JSON but root is not a list
        db.write_text('{"id": 1, "text": "not a list"}', encoding="utf-8")

        # Should raise ValueError with clear message
        with pytest.raises(ValueError, match=r"must be a JSON list|root.*list"):
            storage.load()

    def test_item_not_dict_raises_clear_error(self, tmp_path) -> None:
        """List items that are not dicts should produce clear error message."""
        db = tmp_path / "item_not_dict.json"
        storage = TodoStorage(str(db))

        # Valid JSON list but item is a string, not a dict
        db.write_text('["not a dict", {"id": 1, "text": "valid"}]', encoding="utf-8")

        # Should raise ValueError with clear message about item type
        with pytest.raises(ValueError, match=r"item.*dict|object"):
            storage.load()

    def test_item_missing_id_raises_clear_error(self, tmp_path) -> None:
        """Item missing 'id' field should produce clear error message."""
        db = tmp_path / "missing_id.json"
        storage = TodoStorage(str(db))

        # Valid JSON list but item missing required 'id' field
        db.write_text('[{"text": "task without id"}]', encoding="utf-8")

        # Should raise ValueError with clear message about missing field
        with pytest.raises(ValueError, match=r"missing.*'id'|required.*'id'"):
            storage.load()

    def test_item_missing_text_raises_clear_error(self, tmp_path) -> None:
        """Item missing 'text' field should produce clear error message."""
        db = tmp_path / "missing_text.json"
        storage = TodoStorage(str(db))

        # Valid JSON list but item missing required 'text' field
        db.write_text('[{"id": 1}]', encoding="utf-8")

        # Should raise ValueError with clear message about missing field
        with pytest.raises(ValueError, match=r"missing.*'text'|required.*'text'"):
            storage.load()

    def test_item_wrong_id_type_raises_clear_error(self, tmp_path) -> None:
        """Item with 'id' as string should produce clear error message."""
        db = tmp_path / "wrong_id_type.json"
        storage = TodoStorage(str(db))

        # Valid JSON but 'id' is a string instead of integer
        db.write_text('[{"id": "not-an-int", "text": "task"}]', encoding="utf-8")

        # Should raise ValueError with clear message about type
        with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*integer"):
            storage.load()

    def test_item_wrong_text_type_raises_clear_error(self, tmp_path) -> None:
        """Item with 'text' as non-string should produce clear error message."""
        db = tmp_path / "wrong_text_type.json"
        storage = TodoStorage(str(db))

        # Valid JSON but 'text' is an integer instead of string
        db.write_text('[{"id": 1, "text": 123}]', encoding="utf-8")

        # Should raise ValueError with clear message about type
        with pytest.raises(ValueError, match=r"invalid.*'text'|'text'.*string"):
            storage.load()

    def test_item_null_field_raises_clear_error(self, tmp_path) -> None:
        """Item with null 'id' or 'text' should produce clear error message."""
        db = tmp_path / "null_field.json"
        storage = TodoStorage(str(db))

        # Valid JSON but 'id' is null
        db.write_text('[{"id": null, "text": "task"}]', encoding="utf-8")

        # Should raise ValueError with clear message (case-insensitive match)
        with pytest.raises(ValueError, match=r"(?i)invalid.*'id'"):
            storage.load()

    def test_valid_data_loads_successfully(self, tmp_path) -> None:
        """Valid JSON data should load successfully."""
        db = tmp_path / "valid.json"
        storage = TodoStorage(str(db))

        # Valid JSON with all required fields
        db.write_text('[{"id": 1, "text": "task1"}]', encoding="utf-8")

        todos = storage.load()
        assert len(todos) == 1
        assert todos[0].id == 1
        assert todos[0].text == "task1"

    def test_valid_data_with_optional_fields_loads(self, tmp_path) -> None:
        """Valid JSON with optional fields should load successfully."""
        db = tmp_path / "valid_with_optional.json"
        storage = TodoStorage(str(db))

        # Valid JSON with optional fields
        db.write_text(
            '[{"id": 1, "text": "task1", "done": true, "created_at": "2024-01-01T00:00:00Z"}]',
            encoding="utf-8",
        )

        todos = storage.load()
        assert len(todos) == 1
        assert todos[0].id == 1
        assert todos[0].text == "task1"
        assert todos[0].done is True

    def test_extra_fields_are_ignored(self, tmp_path) -> None:
        """Items with extra unknown fields should be handled gracefully."""
        db = tmp_path / "extra_fields.json"
        storage = TodoStorage(str(db))

        # Valid JSON with extra fields (should be ignored or warned)
        db.write_text('[{"id": 1, "text": "task1", "extra": "field"}]', encoding="utf-8")

        # Should load successfully, ignoring extra fields
        todos = storage.load()
        assert len(todos) == 1
        assert todos[0].id == 1
        assert todos[0].text == "task1"

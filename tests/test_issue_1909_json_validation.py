"""Regression tests for issue #1909: JSON deserialization without schema validation.

Issue: json.loads() in TodoStorage.load() doesn't validate the JSON schema,
allowing malformed JSON to cause unexpected behavior or cryptic errors.

Acceptance criteria:
- Malformed JSON (not a list) raises clear error
- Missing required fields (id, text) are caught with clear error messages
- Type mismatches (id as non-convertible string) are caught with clear error messages

These tests should FAIL with cryptic errors before the fix and PASS with clear
error messages after the fix.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


class TestJSONNotAList:
    """Tests for JSON root not being a list."""

    def test_load_fails_when_json_is_dict(self, tmp_path) -> None:
        """Issue #1909: JSON root is a dict instead of list.

        Before fix: May pass the isinstance check at line 71 if not implemented,
                    or fail with generic error
        After fix: Should raise ValueError with clear message about expecting a list
        """
        db = tmp_path / "todo.json"
        # Write a dict instead of list
        db.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

        storage = TodoStorage(str(db))

        with pytest.raises(ValueError, match=r"must be a JSON list"):
            storage.load()

    def test_load_fails_when_json_is_string(self, tmp_path) -> None:
        """Issue #1909: JSON root is a string instead of list."""
        db = tmp_path / "todo.json"
        db.write_text(json.dumps("not a list"), encoding="utf-8")

        storage = TodoStorage(str(db))

        with pytest.raises(ValueError, match=r"must be a JSON list"):
            storage.load()

    def test_load_fails_when_json_is_number(self, tmp_path) -> None:
        """Issue #1909: JSON root is a number instead of list."""
        db = tmp_path / "todo.json"
        db.write_text(json.dumps(42), encoding="utf-8")

        storage = TodoStorage(str(db))

        with pytest.raises(ValueError, match=r"must be a JSON list"):
            storage.load()


class TestMissingRequiredFields:
    """Tests for missing required fields in todo items."""

    def test_load_fails_when_item_missing_id_field(self, tmp_path) -> None:
        """Issue #1909: Todo item without required 'id' field.

        After fix: Raises ValueError with clear message about missing 'id'
        """
        db = tmp_path / "todo.json"
        # Valid JSON list, but item missing 'id' field
        db.write_text(json.dumps([{"text": "test"}]), encoding="utf-8")

        storage = TodoStorage(str(db))

        with pytest.raises(ValueError, match=r"missing required field.*'id'"):
            storage.load()

    def test_load_fails_when_item_missing_text_field(self, tmp_path) -> None:
        """Issue #1909: Todo item without required 'text' field.

        After fix: Raises ValueError with clear message about missing 'text'
        """
        db = tmp_path / "todo.json"
        db.write_text(json.dumps([{"id": 1}]), encoding="utf-8")

        storage = TodoStorage(str(db))

        with pytest.raises(ValueError, match=r"missing required field.*'text'"):
            storage.load()

    def test_load_fails_when_multiple_items_missing_fields(self, tmp_path) -> None:
        """Issue #1909: Multiple todo items with various missing fields.

        Should catch first validation error and report it clearly.
        """
        db = tmp_path / "todo.json"
        db.write_text(
            json.dumps([{"id": 1}, {"text": "orphan"}, {"id": 3, "text": "valid"}]),
            encoding="utf-8",
        )

        storage = TodoStorage(str(db))

        # Should fail on the first item with missing field
        with pytest.raises(ValueError, match=r"missing required field.*'text'"):
            storage.load()


class TestTypeMismatches:
    """Tests for type validation of todo fields."""

    def test_load_fails_when_id_is_not_convertible_to_int(self, tmp_path) -> None:
        """Issue #1909: Todo 'id' field that cannot be converted to int.

        After fix: Raises ValueError with clear message about 'id' type
        """
        db = tmp_path / "todo.json"
        # id is a complex dict that can't convert to int
        db.write_text(
            json.dumps([{"id": {"not": "an int"}, "text": "test"}]), encoding="utf-8"
        )

        storage = TodoStorage(str(db))

        with pytest.raises(ValueError, match=r"'id' must be a number"):
            storage.load()

    def test_load_fails_when_id_is_none(self, tmp_path) -> None:
        """Issue #1909: Todo 'id' field is null/None.

        This is a common JSON edge case that should be caught explicitly.
        """
        db = tmp_path / "todo.json"
        db.write_text(json.dumps([{"id": None, "text": "test"}]), encoding="utf-8")

        storage = TodoStorage(str(db))

        with pytest.raises(ValueError, match=r"'id' must be a number"):
            storage.load()

    def test_load_fails_when_item_is_not_a_dict(self, tmp_path) -> None:
        """Issue #1909: Todo item in list is not a dict (e.g., string or number).

        After fix: Raises ValueError with clear message
        """
        db = tmp_path / "todo.json"
        # List contains a string instead of dict
        db.write_text(json.dumps(["not a dict"]), encoding="utf-8")

        storage = TodoStorage(str(db))

        with pytest.raises(ValueError, match=r"expected object"):
            storage.load()


class TestValidDataStillWorks:
    """Tests that valid JSON still loads correctly after validation is added."""

    def test_load_succeeds_for_valid_complete_todo(self, tmp_path) -> None:
        """Issue #1909: Valid todo with all fields should load successfully."""
        db = tmp_path / "todo.json"
        db.write_text(
            json.dumps([{"id": 1, "text": "test", "done": True}]), encoding="utf-8"
        )

        storage = TodoStorage(str(db))
        todos = storage.load()

        assert len(todos) == 1
        assert todos[0].id == 1
        assert todos[0].text == "test"
        assert todos[0].done is True

    def test_load_succeeds_for_valid_minimal_todo(self, tmp_path) -> None:
        """Issue #1909: Valid todo with only required fields should load."""
        db = tmp_path / "todo.json"
        db.write_text(json.dumps([{"id": 1, "text": "minimal"}]), encoding="utf-8")

        storage = TodoStorage(str(db))
        todos = storage.load()

        assert len(todos) == 1
        assert todos[0].id == 1
        assert todos[0].text == "minimal"
        assert todos[0].done is False  # Default value

    def test_load_succeeds_for_multiple_valid_todos(self, tmp_path) -> None:
        """Issue #1909: Multiple valid todos should load correctly."""
        db = tmp_path / "todo.json"
        db.write_text(
            json.dumps(
                [
                    {"id": 1, "text": "first"},
                    {"id": 2, "text": "second", "done": True},
                    {"id": 3, "text": "third"},
                ]
            ),
            encoding="utf-8",
        )

        storage = TodoStorage(str(db))
        todos = storage.load()

        assert len(todos) == 3
        assert todos[0].text == "first"
        assert todos[1].text == "second"
        assert todos[2].text == "third"

    def test_load_succeeds_for_empty_list(self, tmp_path) -> None:
        """Issue #1909: Empty list should be valid (no todos)."""
        db = tmp_path / "todo.json"
        db.write_text(json.dumps([]), encoding="utf-8")

        storage = TodoStorage(str(db))
        todos = storage.load()

        assert todos == []

    def test_load_succeeds_when_id_is_string_number(self, tmp_path) -> None:
        """Issue #1909: 'id' as string number like "42" should be convertible."""
        db = tmp_path / "todo.json"
        # JSON id as string is common and should be handled
        db.write_text(json.dumps([{"id": "42", "text": "test"}]), encoding="utf-8")

        storage = TodoStorage(str(db))
        todos = storage.load()

        assert len(todos) == 1
        assert todos[0].id == 42  # Should be converted to int
        assert todos[0].text == "test"

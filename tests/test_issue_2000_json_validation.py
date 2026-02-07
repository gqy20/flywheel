"""Tests for issue #2000: JSON deserialization error handling.

Tests that malformed JSON and missing required fields produce clear error messages
instead of raw stack traces.
"""

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_malformed_json_truncated(tmp_path) -> None:
    """Malformed JSON (truncated file) should produce clear error message."""
    db = tmp_path / "malformed.json"
    storage = TodoStorage(str(db))

    # Create a truncated JSON file
    db.write_text('[{"id": 1, "text": "valid"}, {"id": 2, "text":', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    assert "json" in error_msg or "parse" in error_msg
    assert db.name in error_msg or str(db) in error_msg


def test_storage_load_malformed_json_unmatched_bracket(tmp_path) -> None:
    """Malformed JSON (unmatched bracket) should produce clear error message."""
    db = tmp_path / "unmatched.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with unmatched bracket (missing closing bracket)
    db.write_text('[{"id": 1, "text": "valid"}', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    assert "json" in error_msg or "parse" in error_msg


def test_storage_load_missing_required_id_field(tmp_path) -> None:
    """Valid JSON but missing 'id' field should produce clear error message."""
    db = tmp_path / "no_id.json"
    storage = TodoStorage(str(db))

    # Create valid JSON but missing 'id' field
    db.write_text('[{"text": "todo without id"}]', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    assert "id" in error_msg
    assert "required" in error_msg or "missing" in error_msg


def test_storage_load_missing_required_text_field(tmp_path) -> None:
    """Valid JSON but missing 'text' field should produce clear error message."""
    db = tmp_path / "no_text.json"
    storage = TodoStorage(str(db))

    # Create valid JSON but missing 'text' field
    db.write_text('[{"id": 1}]', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    assert "text" in error_msg
    assert "required" in error_msg or "missing" in error_msg


def test_storage_load_wrong_type_for_id(tmp_path) -> None:
    """Valid JSON but wrong type for 'id' (non-integer) should produce clear error message."""
    db = tmp_path / "bad_id_type.json"
    storage = TodoStorage(str(db))

    # Create valid JSON but 'id' is a string instead of integer
    db.write_text('[{"id": "not-an-int", "text": "todo"}]', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    assert "id" in error_msg
    assert ("type" in error_msg or "integer" in error_msg or "int" in error_msg)


def test_storage_load_valid_json_with_all_fields(tmp_path) -> None:
    """Valid JSON with all required fields should load successfully."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Create valid JSON with all required fields
    db.write_text('[{"id": 1, "text": "valid todo", "done": false}]', encoding="utf-8")

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].id == 1
    assert loaded[0].text == "valid todo"

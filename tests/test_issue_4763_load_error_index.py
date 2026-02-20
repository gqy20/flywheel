"""Tests for Issue #4763: load() error message should include index of malformed record.

When TodoStorage.load() processes a JSON array with malformed data,
the error message should indicate which record (by index) caused the problem.
This makes debugging much easier when dealing with large datasets.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_error_includes_index_for_missing_id_field(tmp_path) -> None:
    """When a record is missing 'id', error message should include the index."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON with 3 records where the 3rd (index 2) is missing 'id'
    db.write_text(
        '[{"id": 1, "text": "valid1"}, {"id": 2, "text": "valid2"}, {"text": "missing id"}]',
        encoding="utf-8",
    )

    # Error should mention index 2 (zero-based) or "3rd" / "third" record
    with pytest.raises(ValueError, match=r"index 2|record 3|item 2|position 2"):
        storage.load()


def test_load_error_includes_index_for_missing_text_field(tmp_path) -> None:
    """When a record is missing 'text', error message should include the index."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON with 5 records where the 2nd (index 1) is missing 'text'
    db.write_text(
        '[{"id": 1, "text": "a"}, {"id": 2}, {"id": 3, "text": "c"}, {"id": 4, "text": "d"}, {"id": 5, "text": "e"}]',
        encoding="utf-8",
    )

    # Error should mention index 1 (zero-based) or "2nd" / "second" record
    with pytest.raises(ValueError, match=r"index 1|record 2|item 1|position 1"):
        storage.load()


def test_load_error_includes_index_for_invalid_id_type(tmp_path) -> None:
    """When a record has invalid 'id' type, error message should include the index."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON with 2 records where the 1st (index 0) has invalid id type
    db.write_text(
        '[{"id": "not-an-int", "text": "bad"}, {"id": 2, "text": "good"}]',
        encoding="utf-8",
    )

    # Error should mention index 0 (zero-based) or "1st" / "first" record
    with pytest.raises(ValueError, match=r"index 0|record 1|item 0|position 0"):
        storage.load()


def test_load_error_includes_index_for_invalid_done_field(tmp_path) -> None:
    """When a record has invalid 'done' field, error message should include the index."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON with 4 records where the 4th (index 3) has invalid done value
    db.write_text(
        '[{"id": 1, "text": "a"}, {"id": 2, "text": "b"}, {"id": 3, "text": "c"}, {"id": 4, "text": "d", "done": "yes"}]',
        encoding="utf-8",
    )

    # Error should mention index 3 (zero-based) or "4th" / "fourth" record
    with pytest.raises(ValueError, match=r"index 3|record 4|item 3|position 3"):
        storage.load()

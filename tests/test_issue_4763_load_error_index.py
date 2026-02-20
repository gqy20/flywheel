"""Tests for error message including index in load() (Issue #4763).

These tests verify that when load() fails due to a malformed record in a JSON array,
the error message includes the index of the problematic record.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_error_includes_index_of_malformed_record(tmp_path) -> None:
    """When load() fails on a malformed record, error message should include the index."""
    db = tmp_path / "malformed_at_index.json"
    storage = TodoStorage(str(db))

    # Create JSON with 3 records where the 3rd record (index 2) is missing 'id'
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}, {"text": "missing id"}]',
        encoding="utf-8",
    )

    # Should raise ValueError with index info (index 2 = 3rd record)
    with pytest.raises(ValueError, match=r"index 2|record 2|item 2|position 2|\[2\]"):
        storage.load()


def test_load_error_includes_index_of_first_malformed_record(tmp_path) -> None:
    """When load() fails, error message should include the index of the first bad record."""
    db = tmp_path / "malformed_at_index_0.json"
    storage = TodoStorage(str(db))

    # Create JSON where the first record (index 0) is missing 'text'
    db.write_text(
        '[{"id": 1}, {"id": 2, "text": "task2"}]',
        encoding="utf-8",
    )

    # Should raise ValueError with index info (index 0 = 1st record)
    with pytest.raises(ValueError, match=r"index 0|record 0|item 0|position 0|\[0\]"):
        storage.load()


def test_load_error_includes_original_error_message(tmp_path) -> None:
    """Error message should include both index and the original error details."""
    db = tmp_path / "malformed_with_details.json"
    storage = TodoStorage(str(db))

    # Create JSON where the second record (index 1) has invalid 'id' type
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": "not-an-int", "text": "task2"}]',
        encoding="utf-8",
    )

    # Should raise ValueError with both index and original error info
    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    # Should contain index info
    assert "index 1" in error_msg or "record 1" in error_msg or "[1]" in error_msg
    # Should also contain info about what was wrong
    assert "id" in error_msg

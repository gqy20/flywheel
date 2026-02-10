"""Regression test for issue #1918: load() should limit file size to prevent DoS.

This test verifies that TodoStorage.load() rejects files larger than the
configured size limit (10MB default) to prevent denial-of-service attacks
via memory exhaustion.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage


def test_load_rejects_oversized_file(tmp_path: Path) -> None:
    """Test that load() raises ValueError for files exceeding size limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a JSON file larger than _MAX_JSON_SIZE_BYTES
    # We'll create a list with enough data to exceed 10MB
    large_data = [{"id": i, "text": "x" * 1000} for i in range(15000)]

    # Write the large file
    db.write_text(json.dumps(large_data), encoding="utf-8")

    # Verify file is actually larger than the limit
    file_size = db.stat().st_size
    assert file_size > _MAX_JSON_SIZE_BYTES, f"Test setup failed: file size {file_size} is not larger than limit {_MAX_JSON_SIZE_BYTES}"

    # Should raise ValueError for oversized file
    with pytest.raises(ValueError, match="JSON file too large"):
        storage.load()


def test_load_accepts_file_within_size_limit(tmp_path: Path) -> None:
    """Test that load() accepts files within the size limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small JSON file well within the limit
    small_data = [
        {"id": 1, "text": "Buy groceries"},
        {"id": 2, "text": "Walk the dog"},
    ]

    db.write_text(json.dumps(small_data), encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].text == "Buy groceries"
    assert todos[1].text == "Walk the dog"


def test_load_handles_file_at_exactly_limit_boundary(tmp_path: Path) -> None:
    """Test that load() accepts files at exactly the size limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create data that's exactly at the limit
    # Each entry is approximately 50 bytes, so we need about 200k entries
    target_size = _MAX_JSON_SIZE_BYTES

    # Create a file that's slightly under the limit
    num_entries = (target_size // 30) - 1000  # Conservative estimate
    data = [{"id": i, "text": "x"} for i in range(num_entries)]

    db.write_text(json.dumps(data), encoding="utf-8")

    # Should load successfully since it's under the limit
    todos = storage.load()
    assert len(todos) == num_entries
    assert todos[0].id == 0


def test_nonexistent_file_returns_empty_list(tmp_path: Path) -> None:
    """Test that load() returns empty list when file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list without error
    todos = storage.load()
    assert todos == []


def test_size_limit_constant_is_defined() -> None:
    """Test that the size limit constant is properly defined."""
    # Verify the constant exists and is 10MB
    assert _MAX_JSON_SIZE_BYTES == 10 * 1024 * 1024

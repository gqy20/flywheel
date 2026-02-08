"""Tests for TOCTOU race condition in TodoStorage.load().

This test suite verifies the fix for issue #2194: load() should verify
data size from actual bytes read, not from stat(), to prevent TOCTOU race.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage
from flywheel.todo import Todo


def test_load_checks_actual_bytes_read_not_stat(tmp_path) -> None:
    """Regression test for issue #2194: TOCTOU race between stat() and read().

    The load() method should check the size of actual bytes read, not the
    file size from stat(). This prevents a TOCTOU race where an attacker
    could replace a small file with a large one between stat() and read().
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small valid JSON file initially
    initial_todos = [Todo(id=1, text="small")]
    db.write_text(json.dumps([t.to_dict() for t in initial_todos]), encoding="utf-8")

    # Simulate TOCTOU: read_text() returns large data despite small file
    # Need to exceed _MAX_JSON_SIZE_BYTES (10MB)
    large_payload = [{"id": i, "text": "x" * 100} for i in range(85000)]
    large_json = json.dumps(large_payload)

    # Use patch.object to mock read_text on the specific Path instance
    with (
        patch.object(Path, "read_text", return_value=large_json),
        pytest.raises(ValueError, match="too large"),
    ):
        storage.load()


def test_load_rejects_oversized_content_from_bytes_read(tmp_path) -> None:
    """Test that load() rejects content based on actual bytes read size."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small file (small stat() size) but make read_text return large data
    initial_todos = [Todo(id=1, text="small")]
    db.write_text(json.dumps([t.to_dict() for t in initial_todos]), encoding="utf-8")

    # Mock read_text to return large data (simulating TOCTOU attack)
    large_payload = [{"id": i, "text": "y" * 100} for i in range(85000)]
    large_json = json.dumps(large_payload)

    with (
        patch.object(Path, "read_text", return_value=large_json),
        pytest.raises(ValueError, match="too large"),
    ):
        storage.load()


def test_load_accepts_content_within_limit_from_bytes_read(tmp_path) -> None:
    """Test that load() accepts content when actual bytes read are within limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a normal-sized JSON file
    todos = [Todo(id=1, text="normal todo"), Todo(id=2, text="another")]
    db.write_text(json.dumps([t.to_dict() for t in todos]), encoding="utf-8")

    # Load should succeed
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "normal todo"
    assert loaded[1].text == "another"


def test_load_empty_string_triggers_size_check_error(tmp_path) -> None:
    """Edge case: ensure empty string is handled correctly in size check."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with some content
    initial_todos = [Todo(id=1, text="test")]
    db.write_text(json.dumps([t.to_dict() for t in initial_todos]), encoding="utf-8")

    # Mock read_text to return empty string (corrupted/empty file after stat)
    with (
        patch.object(Path, "read_text", return_value=""),
        pytest.raises(ValueError, match="Invalid JSON"),
    ):
        storage.load()


def test_max_json_size_bytes_is_10mb() -> None:
    """Verify the size limit is 10MB as documented."""
    assert _MAX_JSON_SIZE_BYTES == 10 * 1024 * 1024

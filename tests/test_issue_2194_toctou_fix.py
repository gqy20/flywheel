"""Tests for issue #2194 - TOCTOU race condition in load().

The bug: load() silently truncates JSON data if file size changes between stat() and read_text().
This is a Time-of-check to Time-of-use (TOCTOU) race condition.

The fix: Read the file content first, then check the size of actual bytes read,
not the stat() size which could be stale.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage
from flywheel.todo import Todo


def test_storage_load_detects_size_from_actual_bytes_not_stat(tmp_path) -> None:
    """Issue #2194: Size limit should use actual bytes read, not stat().

    This tests the TOCTOU scenario where:
    1. stat() reports a small file size (under limit)
    2. File is replaced with a huge file between stat() and read()
    3. read() reads the huge content

    The fix must check the size of actual bytes read, not stat().
    """
    db = tmp_path / "todo.json"

    # Create a valid small JSON file (under the limit)
    small_content = json.dumps([{"id": 1, "text": "small"}])
    db.write_text(small_content, encoding="utf-8")

    # This is the actual content that will be "read" (simulating file growth)
    # Create a huge JSON payload that exceeds the 10MB limit
    huge_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(65000)
    ]
    huge_content = json.dumps(huge_payload)

    # Verify the huge content is actually larger than the limit
    assert len(huge_content.encode("utf-8")) > _MAX_JSON_SIZE_BYTES

    # Mock read_text to return huge content while stat returns small size
    # This simulates the TOCTOU race: stat() sees small file, read() gets huge data
    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        if self == db:
            return huge_content  # Return huge content
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", mock_read_text):
        storage = TodoStorage(str(db))

        # Should raise ValueError because actual bytes read exceed limit
        # even though stat() reports small file size
        with pytest.raises(ValueError, match="too large"):
            storage.load()


def test_storage_load_validates_actual_bytes_read(tmp_path) -> None:
    """Issue #2194: Verify size check works on actual bytes read.

    Normal case: file size reported by stat() matches actual content.
    This should still work correctly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Normal-sized content should work fine
    todos = [Todo(id=1, text="normal todo")]
    storage.save(todos)

    # Load should work normally
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "normal todo"


def test_storage_load_rejects_huge_file_directly(tmp_path) -> None:
    """Issue #2194: Direct huge file (no TOCTOU) should still be rejected.

    This ensures the fix doesn't break the normal oversized file detection.
    """
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a JSON file larger than 10MB
    large_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(65000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Verify the file is actually larger than 10MB
    assert db.stat().st_size > _MAX_JSON_SIZE_BYTES

    # Should raise ValueError for oversized file
    with pytest.raises(ValueError, match="too large"):
        storage.load()

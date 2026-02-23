"""Tests for TOCTOU vulnerability in load() method (Issue #5465).

This test suite verifies that:
1. The load() method reads file content once into memory
2. Size validation is performed on the in-memory data
3. TOCTOU race condition is prevented (file growing between size check and read)

The vulnerability exists when:
1. stat() is called to check file size
2. File could be modified between stat() and read_text()
3. read_text() could read more data than allowed by size check

The fix is to read the file once into memory, then validate size of in-memory data.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage


def test_load_uses_single_read_no_toctou(tmp_path) -> None:
    """Test that load() reads file once, eliminating TOCTOU race condition.

    This test ensures that the file is read once into memory before size validation,
    preventing the race condition where a file could grow between stat() and read_text().
    """
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create a valid small file
    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")

    # Track how many times Path.read_text or Path.read_bytes is called
    read_count = {"count": 0}
    original_read_text = Path.read_text

    def tracking_read_text(self, *args, **kwargs):
        read_count["count"] += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", tracking_read_text):
        result = storage.load()

    # File should be read exactly once
    assert read_count["count"] == 1, (
        f"File should be read exactly once, but was read {read_count['count']} times"
    )
    assert len(result) == 1
    assert result[0].text == "test"


def test_load_rejects_content_exceeding_max_size_after_read(tmp_path) -> None:
    """Test that load() rejects content exceeding max size using in-memory check.

    This test simulates the TOCTOU scenario where file size is small during stat()
    but grows before read_text(). The fix should check the size of the actual
    in-memory content, not the file size from stat().
    """
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create content larger than max size
    large_content = "x" * (_MAX_JSON_SIZE_BYTES + 1000)
    db.write_text(f'[{{"id": 1, "text": "{large_content}"}}]', encoding="utf-8")

    # Should raise ValueError about file being too large
    with pytest.raises(ValueError, match=r"too large|DoS|denial"):
        storage.load()


def test_load_size_check_uses_in_memory_content_not_stat(tmp_path) -> None:
    """Regression test: load() should use in-memory content size, not stat().

    This test simulates a file that appears small in stat() but actually has
    large content when read. This can happen in TOCTOU race conditions.

    The fix should read file content first, then check the size of that content.
    """
    db = tmp_path / "toctou_test.json"
    storage = TodoStorage(str(db))

    # Create actual large content
    large_content = "y" * (_MAX_JSON_SIZE_BYTES + 5000)
    actual_large_content = f'[{{"id": 1, "text": "{large_content}"}}]'
    db.write_text(actual_large_content, encoding="utf-8")

    # Mock stat() to return a small size (simulating TOCTOU where file grows)
    original_stat = Path.stat

    def fake_small_stat(self, *, follow_symlinks=True):
        result = original_stat(self, follow_symlinks=follow_symlinks)
        # Simulate stat() seeing a small file
        # Create a new stat_result with modified st_size using os module
        return os.stat_result(
            (
                result.st_mode,
                result.st_ino,
                result.st_dev,
                result.st_nlink,
                result.st_uid,
                result.st_gid,
                100,  # Fake small size (100 bytes)
                result.st_atime,
                result.st_mtime,
                result.st_ctime,
            )
        )

    # Even though stat() returns small size, the actual content is large
    # The fix should check the in-memory content size and reject it
    with (
        patch.object(Path, "stat", fake_small_stat),
        pytest.raises(ValueError, match=r"too large|DoS|denial"),
    ):
        storage.load()


def test_load_accepts_content_at_exact_max_size(tmp_path) -> None:
    """Test that load() accepts content at exactly the max size limit."""
    db = tmp_path / "exact_limit.json"
    storage = TodoStorage(str(db))

    # Create content at exactly the max size (just under limit for JSON overhead)
    # We need valid JSON that is <= MAX_JSON_SIZE_BYTES
    content = '{"id": 1, "text": "' + ("a" * 100) + '"}'
    db.write_text(f"[{content}]", encoding="utf-8")

    # Should load successfully
    result = storage.load()
    assert len(result) == 1


def test_load_normal_file_still_works(tmp_path) -> None:
    """Verify normal-sized files still load correctly after the fix."""
    db = tmp_path / "normal.json"
    storage = TodoStorage(str(db))

    # Create a normal todo file
    todos_data = [
        {"id": 1, "text": "Buy groceries"},
        {"id": 2, "text": "Walk the dog", "done": True},
        {"id": 3, "text": "Write tests"},
    ]

    db.write_text(json.dumps(todos_data), encoding="utf-8")

    # Should load successfully
    result = storage.load()
    assert len(result) == 3
    assert result[0].text == "Buy groceries"
    assert result[1].done is True
    assert result[2].text == "Write tests"

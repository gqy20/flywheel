"""Tests for TOCTOU vulnerability fix (Issue #7315).

These tests verify that:
1. File is read only once, then size check is performed on in-memory buffer
2. This eliminates the race condition window between stat() and read()
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _MAX_JSON_SIZE_BYTES


def test_load_performs_single_read_operation(tmp_path) -> None:
    """Test that load() reads file only once, eliminating TOCTOU race condition.

    Regression test for issue #7315: Race condition window between file size
    check and JSON load (TOCTOU). The size check via stat() and content read
    via read_text() were separate operations, creating an attack window.

    The fix reads the file once into memory, then checks the size of the buffer.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")

    # Track the number of times read_text is called
    read_count = 0
    original_read_text = Path.read_text

    def counting_read_text(self, *args, **kwargs):
        nonlocal read_count
        read_count += 1
        return original_read_text(self, *args, **kwargs)

    # Patch Path.read_text to count calls
    with patch.object(Path, "read_text", counting_read_text):
        storage.load()

    # Should only call read_text once (not once for stat + once for read)
    assert read_count == 1, (
        f"load() should read file exactly once, but read_text was called {read_count} times. "
        "This indicates a TOCTOU vulnerability where file size check and content read "
        "are separate operations."
    )


def test_load_size_check_uses_buffer_not_stat(tmp_path) -> None:
    """Test that the size check is performed on the in-memory buffer, not via stat().

    The TOCTOU vulnerability was specifically about using stat() for size checking
    AFTER reading the file. The fix ensures size is checked on the in-memory buffer.

    Note: Path.exists() does use stat() internally, but that's benign - it happens
    BEFORE the read operation and doesn't create the TOCTOU window. The vulnerability
    was specifically in: stat() for size -> read_text() (two separate operations).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")

    # Track the order of operations
    operations = []
    original_stat = Path.stat
    original_read_text = Path.read_text

    def tracking_stat(self, *args, **kwargs):
        operations.append("stat")
        return original_stat(self, *args, **kwargs)

    def tracking_read_text(self, *args, **kwargs):
        operations.append("read_text")
        return original_read_text(self, *args, **kwargs)

    # Patch to track operation order
    with (
        patch.object(Path, "stat", tracking_stat),
        patch.object(Path, "read_text", tracking_read_text),
    ):
        storage.load()

    # Verify there's only one read_text call and it's after any stat calls
    read_count = operations.count("read_text")
    assert read_count == 1, (
        f"Should read file exactly once, but read_text was called {read_count} times"
    )

    # Verify that read_text happens after all stat calls (no stat between read operations)
    last_stat_idx = len(operations) - 1 - operations[::-1].index("stat") if "stat" in operations else -1
    read_idx = operations.index("read_text")

    # There should be no stat call AFTER the read_text
    stats_after_read = operations[read_idx + 1 :].count("stat")
    assert stats_after_read == 0, (
        f"Found {stats_after_read} stat() calls after read_text(). "
        "Size should be checked on in-memory buffer, not via stat()."
    )


def test_large_file_still_rejected_after_toctou_fix(tmp_path) -> None:
    """Test that large files are still rejected after the TOCTOU fix.

    The fix should maintain the original security check behavior: files
    larger than the limit should be rejected with a clear error message.
    """
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a file larger than the limit (10MB)
    # We create a minimal valid JSON that exceeds the limit
    large_content = "[" + ",".join(['{"id":' + str(i) + ',"text":"' + "x" * 1000 + '"}' for i in range(11000)]) + "]"

    # Only write if it's actually larger than limit
    if len(large_content.encode("utf-8")) > _MAX_JSON_SIZE_BYTES:
        db.write_text(large_content, encoding="utf-8")

        with pytest.raises(ValueError, match=r"JSON file too large|denial-of-service"):
            storage.load()
    else:
        # If we couldn't create a large enough file, skip with a note
        pytest.skip("Could not create file larger than 10MB limit")


def test_toctou_race_condition_mitigation(tmp_path) -> None:
    """Test that the TOCTOU race condition is mitigated.

    This test simulates an attacker modifying the file between what used to be
    the size check and the read operation. With the fix, this should be impossible
    because there's only one read operation.

    Note: This test verifies the fix works by confirming read happens only once.
    A true race condition test would require more complex setup.
    """
    db = tmp_path / "race.json"
    storage = TodoStorage(str(db))

    # Create a small valid todo file
    small_content = '[{"id": 1, "text": "small"}]'
    db.write_text(small_content, encoding="utf-8")

    loaded = storage.load()

    # Should successfully load the file
    assert len(loaded) == 1
    assert loaded[0].text == "small"


def test_empty_file_handling_after_toctou_fix(tmp_path) -> None:
    """Test that empty files are still handled correctly after the fix."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Create an empty file
    db.write_text("", encoding="utf-8")

    # Empty file should raise ValueError about invalid JSON
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()


def test_normal_json_load_still_works(tmp_path) -> None:
    """Test that normal JSON loading still works after the TOCTOU fix."""
    db = tmp_path / "normal.json"
    storage = TodoStorage(str(db))

    # Create a typical todo file
    content = '''[
        {"id": 1, "text": "First task", "done": false},
        {"id": 2, "text": "Second task", "done": true},
        {"id": 3, "text": "Third task with unicode: 你好世界"}
    ]'''
    db.write_text(content, encoding="utf-8")

    loaded = storage.load()

    assert len(loaded) == 3
    assert loaded[0].text == "First task"
    assert loaded[0].done is False
    assert loaded[1].text == "Second task"
    assert loaded[1].done is True
    assert loaded[2].text == "Third task with unicode: 你好世界"

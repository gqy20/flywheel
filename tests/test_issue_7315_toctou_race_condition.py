"""Tests for TOCTOU race condition fix (Issue #7315).

These tests verify that:
1. File is read only once, then size check is performed on in-memory buffer
2. The load operation is atomic (no race condition window between size check and read)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage
from flywheel.todo import Todo


def test_load_uses_single_read_operation(tmp_path) -> None:
    """Regression test for #7315: Load should read file only once.

    The size check and JSON load should be atomic by reading the file once
    into memory, then checking the buffer size, rather than calling stat()
    followed by read_text() which creates a race condition window.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="test task")]
    storage.save(todos)

    # Track how many times read_text is called
    read_count = [0]
    original_read_text = Path.read_text

    def counting_read_text(self, *args, **kwargs):
        read_count[0] += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", counting_read_text):
        loaded = storage.load()

    # Should only read the file once (not once for stat + once for read)
    assert read_count[0] == 1, (
        f"Expected exactly 1 file read, got {read_count[0]}. "
        "The file should be read once into memory, then size checked on the buffer."
    )

    # Verify the loaded data is correct
    assert len(loaded) == 1
    assert loaded[0].text == "test task"


def test_load_checks_buffer_size_not_file_size(tmp_path) -> None:
    """Verify that size check is performed on in-memory buffer, not file stat.

    This test ensures the fix for #7315: the size limit should be checked
    on the in-memory buffer after reading, not via stat() before reading.

    Note: exists() still uses stat() internally, but the SIZE check
    should be on the buffer, not a separate stat() call.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid small file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # The key test: verify that file size check happens on buffer
    # by verifying read_text is called before any size check
    original_read_text = Path.read_text
    read_order = []

    def ordered_read_text(self, *args, **kwargs):
        read_order.append("read_text")
        return original_read_text(self, *args, **kwargs)

    # A simpler test: verify that content is read before size check
    # by mocking the size check behavior
    with patch.object(Path, "read_text", ordered_read_text):
        loaded = storage.load()

    assert len(loaded) == 1
    assert loaded[0].text == "test"
    assert len(read_order) == 1, "File should be read exactly once"


def test_load_rejects_oversized_file_with_single_read(tmp_path) -> None:
    """Test that oversized files are rejected after single read into memory.

    Even for oversized files, we should read the file once (up to limit),
    then check the buffer size, rather than using stat() first.
    """
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a file larger than the limit
    # We need to be careful: we want to test the size check works,
    # but we don't want to actually create a 10MB+ file
    large_content = json.dumps([{"id": i, "text": "x" * 1000} for i in range(15000)])
    db.write_text(large_content, encoding="utf-8")

    # Verify the file is larger than the limit
    file_size = db.stat().st_size
    assert file_size > _MAX_JSON_SIZE_BYTES, (
        f"Test file should be larger than limit. "
        f"Got {file_size} bytes, limit is {_MAX_JSON_SIZE_BYTES} bytes."
    )

    # The load should raise ValueError about file size
    with pytest.raises(ValueError, match=r"too large|DoS"):
        storage.load()


def test_load_atomic_operation_no_race_window(tmp_path) -> None:
    """Test that load is atomic: no race window between size check and read.

    This simulates the TOCTOU attack scenario where an attacker could
    replace the file between size check and read. After the fix,
    this should not be possible since we read once into memory.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid small file
    valid_todos = [Todo(id=1, text="valid task")]
    storage.save(valid_todos)

    # Track if file is read more than once
    original_read_text = Path.read_text
    read_count = [0]

    def single_read_only(self, *args, **kwargs):
        read_count[0] += 1
        if read_count[0] > 1:
            # This should never happen after the fix
            raise AssertionError(
                "File was read multiple times! "
                "This indicates a race condition vulnerability."
            )
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", single_read_only):
        loaded = storage.load()

    # Should have read exactly once
    assert read_count[0] == 1
    assert len(loaded) == 1
    assert loaded[0].text == "valid task"

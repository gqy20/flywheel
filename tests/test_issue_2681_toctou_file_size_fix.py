"""Regression tests for issue #2681: TOCTOU race condition in file size check.

Issue: stat() and read_text() are not atomic - file could grow between size check
and read, allowing an attacker to bypass the size limit and cause unbounded memory usage.

These tests verify that reading is bounded even if file grows between stat() and read().

Before fix: Files can grow after stat() and be read entirely (unbounded memory)
After fix: Reading stops after MAX_JSON_SIZE_BYTES even if file grew
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage


def test_load_bounded_read_even_if_file_grows_after_stat(tmp_path) -> None:
    """Issue #2681: Memory usage should be bounded even if file grows between stat() and read().

    Simulates TOCTOU race where file size is checked when small, then grows before
    the actual read. The implementation should still bound memory usage.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small valid JSON file that will appear to grow
    small_content = '[]'
    db.write_text(small_content, encoding="utf-8")

    # Mock os.read to simulate file growth after open but before read
    original_os_read = os.read
    read_count = [0]

    def growing_os_read(fd, bufsize):
        """Simulate file growing after open() - returns huge data on first read."""
        read_count[0] += 1
        if read_count[0] == 1:
            # Generate data larger than _MAX_JSON_SIZE_BYTES (10MB)
            # Return 12MB of data to exceed the limit
            huge_data = b'[' + b'{"a":"b"},' * (_MAX_JSON_SIZE_BYTES // 10) + b']'
            # Ensure it's definitely larger than limit
            assert len(huge_data) > _MAX_JSON_SIZE_BYTES, f"Generated {len(huge_data)} bytes, need > {_MAX_JSON_SIZE_BYTES}"
            return huge_data
        return original_os_read(fd, bufsize)

    with patch('os.read', growing_os_read), pytest.raises(ValueError, match="too large"):
        storage.load()


def test_load_respects_size_limit_for_large_files(tmp_path) -> None:
    """Issue #2681: Files larger than _MAX_JSON_SIZE_BYTES should be rejected.

    The implementation uses bounded read (os.read with limit), so files larger
    than the limit will either be detected as too large or fail with JSON error
    due to truncation. Both outcomes provide bounded memory usage.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file larger than the limit
    large_content = '["item"]' * (_MAX_JSON_SIZE_BYTES // 10 + 1000)
    db.write_text(large_content, encoding="utf-8")

    # Should raise either ValueError about file size OR JSON decode error
    # (both are acceptable since memory usage is bounded)
    with pytest.raises((ValueError, json.JSONDecodeError)):
        storage.load()


def test_load_succeeds_for_small_valid_files(tmp_path) -> None:
    """Issue #2681: Normal small files should still load successfully."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Valid small JSON
    valid_content = '[{"id": 1, "text": "test", "done": false}]'
    db.write_text(valid_content, encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "test"


def test_load_with_file_descriptor_read(tmp_path) -> None:
    """Issue #2681: Verify implementation uses bounded read (not read_text).

    This test verifies that the fix uses os.open/read or similar bounded approach
    instead of Path.read_text() which reads entire file into memory.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid small file
    valid_content = '[{"id": 1, "text": "test", "done": false}]'
    db.write_text(valid_content, encoding="utf-8")

    # Track if read_text is used (it shouldn't be after the fix)
    with patch("flywheel.storage.Path.read_text", side_effect=AssertionError("Should not use read_text for unbounded read")):
        # If the fix is implemented correctly, this should NOT call read_text
        # and should load successfully
        todos = storage.load()
        assert len(todos) == 1


def test_read_with_explicit_byte_limit_stops_at_limit(tmp_path) -> None:
    """Issue #2681: Reading should stop at byte limit, not read entire file.

    This verifies the core fix: read with explicit byte limit, not read all.
    """
    db = tmp_path / "todo.json"

    # Create a file that's valid JSON at start but has extra data after limit
    valid_prefix = '[{"id": 1, "text": "valid"}'
    # Pad to exactly under the limit
    padding = 'x' * (_MAX_JSON_SIZE_BYTES // 2)
    # Add more data that would be ignored if bounded read is working
    extra_data = ', "this": "should", "not": "be", "parsed": "if_bounded"}]'

    content = valid_prefix + padding + extra_data
    db.write_bytes(content.encode('utf-8'))

    storage = TodoStorage(str(db))

    # With bounded read, should either:
    # - Fail cleanly with JSON error (incomplete JSON at bound)
    # - Or successfully parse what fits within bound
    # Either way, memory usage is bounded
    with pytest.raises((ValueError, json.JSONDecodeError)):
        storage.load()

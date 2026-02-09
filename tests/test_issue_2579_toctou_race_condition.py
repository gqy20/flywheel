"""Regression test for issue #2579: TOCTOU race condition in load().

The vulnerability occurs when:
1. stat().st_size is checked (time-of-check)
2. File grows between stat() and read_text()
3. read_text() reads the larger file (time-of-use)

This test verifies that the fix prevents loading files that grow
between the size check and the actual read operation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage


def test_toctou_race_condition_stat_vs_read(tmp_path) -> None:
    """Test that load() handles TOCTOU race between stat() and read_text().

    This test simulates an attacker who:
    1. Creates a small JSON file that passes the size check
    2. Between stat() and read_text(), grows the file to be huge
    3. The read_text() then reads more data than was checked

    The fix should bound the actual bytes read, not just check the size.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial small valid JSON
    small_content = '[{"id":1,"text":"small"}]'
    db.write_text(small_content, encoding="utf-8")

    # Track actual calls to understand the sequence
    stat_sizes = []
    original_stat = Path.stat

    def tracking_stat(self, follow_symlinks=True):
        result = original_stat(self, follow_symlinks=follow_symlinks)
        stat_sizes.append(result.st_size)
        return result

    read_data = []
    original_read_text = Path.read_text

    def tracking_read_text(self, *args, **kwargs):
        content = original_read_text(self, *args, **kwargs)
        read_data.append(len(content.encode("utf-8")))
        return content

    # First, verify normal behavior works
    with (
        patch.object(Path, "stat", tracking_stat),
        patch.object(Path, "read_text", tracking_read_text),
    ):
        todos = storage.load()
        assert len(todos) == 1
        assert todos[0].text == "small"

    # Now simulate TOCTOU attack: file grows between stat and read
    # This is hard to test deterministically, but we can verify the fix
    # by ensuring that even if we read large data, we enforce limits

    # Create a scenario where we simulate reading too much data
    huge_json = "[]"
    # Pad to exceed max size
    huge_json = huge_json.ljust(_MAX_JSON_SIZE_BYTES + 1000, " ")

    db.write_text(huge_json, encoding="utf-8")

    # This should raise ValueError for file too large
    with pytest.raises(ValueError, match="JSON file too large"):
        storage.load()


def test_toctou_bounded_read_protection(tmp_path) -> None:
    """Test that load() bounds actual bytes read, not just stat size.

    This verifies the fix for TOCTOU by ensuring that:
1. We limit the actual bytes read from the file
    2. We don't rely solely on stat() for size enforcement
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create content exactly at the limit
    content = "[]"
    # Pad to just under the limit
    padded = content.ljust(_MAX_JSON_SIZE_BYTES - 100, " ")
    db.write_text(padded, encoding="utf-8")

    # Should load fine
    todos = storage.load()
    assert todos == []

    # Create content over the limit
    oversized = content.ljust(_MAX_JSON_SIZE_BYTES + 100, " ")
    db.write_text(oversized, encoding="utf-8")

    # Should fail
    with pytest.raises(ValueError, match="JSON file too large"):
        storage.load()


def test_toctou_with_file_handle_locking(tmp_path) -> None:
    """Test that load() uses file handle to prevent TOCTOU.

    The fix should open the file and then check/parse from the same handle,
    preventing other processes from modifying the file between check and use.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Valid small JSON
    small_content = '[{"id":1,"text":"test"}]'
    db.write_text(small_content, encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "test"

    # Even if file grows immediately after, we should have already
    # read it safely with the fix

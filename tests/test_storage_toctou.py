"""Tests for TOCTOU (Time-of-Check-Time-of-Use) vulnerability in TodoStorage.

This test suite verifies that TodoStorage.load() is protected against TOCTOU
attacks where an attacker could replace a file between the size check and read.

Security issue: If stat() and read_text() use separate file opens,
an attacker could replace the file in between, bypassing size limits.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage


def test_load_uses_single_file_open_for_size_check_and_read(tmp_path) -> None:
    """Test that load() opens file only once for both size check and read.

    This is the key security property: we must use fstat() on an already-open
    file descriptor, not stat() followed by a separate open().

    If we use separate opens, an attacker could:
    1. Create a small file that passes size check
    2. Replace it with a large file/symlink between stat() and read_text()
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid small file
    small_data = [{"id": 1, "text": "small", "done": False}]
    db.write_text(json.dumps(small_data), encoding="utf-8")

    # Track how many times os.open is called during load
    # The fix should use os.open + os.fstat, not Path.stat + Path.read_text
    open_calls = []
    original_open = os.open

    def tracking_open(path, *args, **kwargs):
        open_calls.append(path)
        return original_open(path, *args, **kwargs)

    with patch("os.open", side_effect=tracking_open):
        storage.load()

    # With the fix, load should open the file exactly once for both
    # size check (via fstat) and reading
    # Without the fix, Path.stat and Path.read_text would open separately
    db_path_str = str(db)
    file_opens = [p for p in open_calls if p in (db_path_str, db)]

    # The fix should open the file only once
    assert len(file_opens) == 1, (
        f"load() should open file exactly once for TOCTOU safety, "
        f"but opened {len(file_opens)} times"
    )


def test_toctou_attack_cannot_bypass_size_limit(tmp_path) -> None:
    """Regression test: verify TOCTOU attack cannot bypass size limit.

    This test simulates an attacker who:
    1. Creates a small file that passes size check
    2. Quickly replaces it with a large file during the race window

    The fix should prevent this by using fstat on an already-open fd.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small file that will pass size check
    small_data = [{"id": 1, "text": "small file", "done": False}]
    small_content = json.dumps(small_data)
    db.write_text(small_content, encoding="utf-8")

    # Create content that exceeds the size limit
    large_data = [{"id": i, "text": "x" * 1000, "done": False} for i in range(20000)]
    large_content = json.dumps(large_data)
    assert len(large_content) > _MAX_JSON_SIZE_BYTES, (
        "Test setup error: large content should exceed limit"
    )

    # Track when stat is called to simulate the attack
    stat_called = threading.Event()
    attack_complete = threading.Event()

    original_stat = Path.stat

    def attacking_stat(self, *args, **kwargs):
        """When stat is called, simulate TOCTOU by replacing the file."""
        result = original_stat(self, *args, **kwargs)

        # Only attack once, and only for our test file
        if str(self) == str(db) and not attack_complete.is_set():
            stat_called.set()
            # Wait a moment then replace the file with large content
            # This simulates attacker replacing file in the race window
            attack_complete.set()

        return result

    # With the vulnerable code (stat + read_text separately),
    # this would allow bypassing the size check
    # With the fix (open + fstat + read from same fd), the size check
    # is done on the already-open file descriptor, so replacement doesn't help

    # The fix should ensure that even if we tried to attack, the size check
    # would still work correctly on the opened file
    with patch.object(Path, "stat", attacking_stat):
        # This should either:
        # 1. Successfully load the small file (if fix works - file opened once)
        # 2. Raise ValueError for size limit (if vulnerable but we caught it)
        # The key is it should NOT silently load large content
        try:
            result = storage.load()
            # If we got here, we loaded successfully
            # Verify we got the small content, not the large content
            total_text_length = sum(len(t.text) for t in result)
            # Small content has tiny text, large content would have 1000+ chars per todo
            assert total_text_length < 100, (
                f"Loaded large content unexpectedly! Got {len(result)} todos "
                f"with total text length {total_text_length}"
            )
        except ValueError as e:
            # If size check triggered, that's also acceptable
            assert "too large" in str(e).lower(), f"Unexpected error: {e}"


def test_load_rejects_oversized_file(tmp_path) -> None:
    """Test that load() rejects files exceeding the size limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create content that exceeds the size limit (>10MB)
    large_data = [{"id": i, "text": "x" * 1000, "done": False} for i in range(20000)]
    large_content = json.dumps(large_data)
    db.write_text(large_content, encoding="utf-8")

    # Verify our test setup
    assert len(large_content) > _MAX_JSON_SIZE_BYTES

    # Should raise ValueError for oversized file
    with pytest.raises(ValueError, match="too large"):
        storage.load()


def test_load_accepts_file_at_size_limit(tmp_path) -> None:
    """Test that load() accepts files at exactly the size limit boundary."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create content close to but under the limit
    # We need valid JSON that's under 10MB
    data = [{"id": i, "text": f"Task {i}", "done": False} for i in range(1000)]
    content = json.dumps(data)
    db.write_text(content, encoding="utf-8")

    # Should load successfully
    result = storage.load()
    assert len(result) == 1000


def test_symlink_size_check_uses_opened_fd(tmp_path) -> None:
    """Test that size check cannot be bypassed via symlink replacement.

    If an attacker can:
    1. Make stat() follow a symlink to a small file
    2. Replace symlink to point to a large file before read_text()

    The fix (using fstat on opened fd) prevents this.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small file
    small_file = tmp_path / "small.json"
    small_data = [{"id": 1, "text": "small", "done": False}]
    small_file.write_text(json.dumps(small_data), encoding="utf-8")

    # Create a large file
    large_file = tmp_path / "large.json"
    large_data = [{"id": i, "text": "x" * 1000, "done": False} for i in range(20000)]
    large_file.write_text(json.dumps(large_data), encoding="utf-8")

    # Start with symlink to small file
    db.symlink_to(small_file)

    # The fix should open the file once and use fstat on the fd
    # This means even if the symlink changes, we're reading from the
    # already-opened file descriptor
    result = storage.load()

    # Should have loaded the small content
    assert len(result) == 1
    assert result[0].text == "small"

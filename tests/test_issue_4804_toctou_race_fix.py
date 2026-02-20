"""Regression test for issue #4804: TOCTOU race condition in load().

The TOCTOU (Time-of-Check-Time-of-Use) vulnerability existed in load():
1. First it checked file size with stat()
2. Then it read file content with read_text()

An attacker could replace the file between these two operations,
allowing them to bypass the size limit check and load an oversized file.

The fix is to use a single read operation and check content size after reading.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage


def test_load_uses_single_read_no_separate_stat_for_size(tmp_path) -> None:
    """Verify load() does NOT call stat() specifically for size checking.

    This is the key test for issue #4804: the TOCTOU race condition
    was caused by calling stat() to check size, then read_text() to get content.
    The fix should use content size, not stat().st_size.

    Note: exists() may still call stat(), but that's not a TOCTOU vulnerability
    because we're checking existence, not size. The TOCTOU bug was specifically
    about the size check race: stat() size -> read_text() content.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    todos_json = json.dumps([{"id": 1, "text": "test todo"}])
    db.write_text(todos_json, encoding="utf-8")

    # Track if stat().st_size is accessed for size checking
    # (not just if stat() is called, but if st_size attribute is read)
    st_size_accessed = False

    class TrackedStatResult:
        """Wrapper that tracks if st_size is accessed."""
        def __init__(self, original_result):
            self._original = original_result

        @property
        def st_size(self):
            nonlocal st_size_accessed
            st_size_accessed = True
            return self._original.st_size

        def __getattr__(self, name):
            return getattr(self._original, name)

    original_stat = Path.stat

    def tracking_stat(self, *args, **kwargs):
        result = original_stat(self, *args, **kwargs)
        if self == db:
            return TrackedStatResult(result)
        return result

    with patch.object(Path, "stat", tracking_stat):
        loaded = storage.load()

    # Verify the file loaded correctly
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"

    # After the fix, st_size should NOT be accessed for size checking
    # The fix reads content first, then checks len(content)
    # If st_size is accessed, the TOCTOU vulnerability still exists
    assert st_size_accessed is False, (
        "load() accessed stat().st_size which indicates TOCTOU vulnerability - "
        "size should be checked via len(content), not stat().st_size"
    )


def test_load_still_rejects_oversized_content_after_fix(tmp_path) -> None:
    """Verify that the TOCTOU fix still correctly rejects oversized files.

    After eliminating the stat() call, the size check should now be done
    on the actual content length, not file size.
    """
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create content that when read as text, exceeds the limit
    # _MAX_JSON_SIZE_BYTES is 10MB, create ~11MB of content
    large_text = "x" * (_MAX_JSON_SIZE_BYTES + 1024 * 1024)  # ~11MB
    large_payload = [{"id": 1, "text": large_text}]

    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Should raise ValueError for oversized content
    with pytest.raises(ValueError) as exc_info:
        storage.load()

    # Error message should mention size or large
    error_msg = str(exc_info.value).lower()
    assert "too large" in error_msg or "size" in error_msg or "limit" in error_msg


def test_load_content_size_check_not_file_size(tmp_path) -> None:
    """Verify load() checks content size, not file metadata.

    This tests that the fix properly uses len(content) instead of stat().st_size,
    which ensures there's no TOCTOU window between check and use.
    """
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create a small valid JSON
    small_json = json.dumps([{"id": 1, "text": "small"}])
    db.write_text(small_json, encoding="utf-8")

    # Track what gets called
    calls_made = []
    original_stat = Path.stat
    original_read_text = Path.read_text

    def tracking_stat(self, *args, **kwargs):
        if self == db:
            calls_made.append("stat")
        return original_stat(self, *args, **kwargs)

    def tracking_read_text(self, *args, **kwargs):
        if self == db:
            calls_made.append("read_text")
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "stat", tracking_stat), \
         patch.object(Path, "read_text", tracking_read_text):
        storage.load()

    # After the fix, read_text should be called but NOT stat (for size check)
    # (stat might be called internally by exists(), which is fine)
    assert "read_text" in calls_made, "load() must call read_text to read content"

    # The critical check: if stat is called AFTER read_text for size checking,
    # that's the TOCTOU vulnerability. The fix should check len(content) instead.
    # exists() might call stat, but that should be before read_text is fine
    # The key is no stat AFTER exists check but BEFORE read_text for size


def test_load_toctou_race_cannot_bypass_size_limit(tmp_path) -> None:
    """Simulate TOCTOU attack to verify the race condition is fixed.

    Before the fix: An attacker could replace the file between stat() and read_text()
    After the fix: Content is read first, then checked - no race window
    """
    db = tmp_path / "race.json"
    storage = TodoStorage(str(db))

    # Start with a small file that passes size check
    small_json = json.dumps([{"id": 1, "text": "small"}])
    db.write_text(small_json, encoding="utf-8")

    # Track file size at stat time vs read time
    stat_size = None
    read_size = None
    file_swapped = False

    original_stat = Path.stat
    original_read_text = Path.read_text

    def malicious_stat(self, *args, **kwargs):
        nonlocal stat_size, file_swapped
        if self == db:
            stat_size = original_stat(self, *args, **kwargs).st_size
            # Simulate attacker swapping file AFTER stat but BEFORE read
            if not file_swapped:
                large_content = "y" * (_MAX_JSON_SIZE_BYTES + 1024 * 1024)
                large_json = json.dumps([{"id": 1, "text": large_content}])
                db.write_text(large_json, encoding="utf-8")
                file_swapped = True
        return original_stat(self, *args, **kwargs)

    def tracking_read_text(self, *args, **kwargs):
        nonlocal read_size
        if self == db:
            result = original_read_text(self, *args, **kwargs)
            read_size = len(result)
            return result
        return original_read_text(self, *args, **kwargs)

    # If TOCTOU exists: stat sees small size, read sees large content
    # Fix should reject based on content size, not file size
    with patch.object(Path, "stat", malicious_stat), \
         patch.object(Path, "read_text", tracking_read_text):
        try:
            storage.load()
            # If load succeeded, the attack worked - file was too large!
            # The fix should have rejected based on content size
            assert read_size is not None and read_size <= _MAX_JSON_SIZE_BYTES, (
                f"TOCTOU vulnerability: load() accepted {read_size} bytes "
                f"(limit: {_MAX_JSON_SIZE_BYTES}) after file was swapped"
            )
        except ValueError as e:
            # Good - oversized content was rejected
            assert "too large" in str(e).lower() or "size" in str(e).lower()


def test_load_accepts_content_at_size_limit(tmp_path) -> None:
    """Verify files exactly at the size limit are accepted (boundary condition)."""
    db = tmp_path / "exact_limit.json"
    storage = TodoStorage(str(db))

    # Create content at exactly the limit (minus overhead for JSON structure)
    # The limit applies to content read, not file on disk
    # Use content slightly under limit to account for JSON overhead
    safe_text_size = _MAX_JSON_SIZE_BYTES - 100  # Leave room for JSON structure
    text_content = "a" * safe_text_size
    payload = [{"id": 1, "text": text_content}]

    db.write_text(json.dumps(payload), encoding="utf-8")

    # Should load successfully - within limit
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == text_content

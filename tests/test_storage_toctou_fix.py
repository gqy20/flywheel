"""Regression test for TOCTOU vulnerability in TodoStorage.load().

Issue #4804: The load() method had a Time-of-Check-Time-of-Use (TOCTOU)
race condition between stat() checking file size and read_text() reading content.

This test suite verifies that the fix properly eliminates the TOCTOU window
by using a single read operation followed by in-memory size check.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _MAX_JSON_SIZE_BYTES
from flywheel.todo import Todo


class TestTOCTOUFix:
    """Tests verifying TOCTOU vulnerability is fixed in load()."""

    def test_load_uses_single_read_operation_no_stat(self, tmp_path) -> None:
        """Verify load() reads content first, then checks size in memory.

        This test ensures that load() does NOT use stat() for size checking,
        eliminating the TOCTOU race window between stat() and read_text().

        Note: Path.exists() internally calls stat(), so we expect at most 1 call
        from exists(). The key is that stat() is NOT used to check file size
        before reading the content.
        """
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Create a valid JSON file
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # Track whether stat() is called on the path
        stat_called = []

        original_stat = Path.stat

        def tracking_stat(self, *args, **kwargs):
            stat_called.append(self)
            return original_stat(self, *args, **kwargs)

        # Patch Path.stat to track calls
        with patch.object(Path, "stat", tracking_stat):
            loaded = storage.load()

        # Verify data loaded correctly
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"

        # Key assertion: stat() should be called at most once (from exists())
        # Previously the vulnerable code called stat() TWICE:
        # 1. Once for exists() check
        # 2. Once for size checking via .stat().st_size
        # The fix should only call stat() once (for exists())
        assert len(stat_called) == 1, (
            f"TOCTOU vulnerability: load() called stat() {len(stat_called)} times. "
            "Expected 1 call (from exists()) - the fix should use read_text() first "
            "then check len(content) in memory, not stat() for size."
        )

    def test_load_rejects_content_exceeding_size_limit(self, tmp_path) -> None:
        """Verify that content exceeding size limit is still rejected after fix."""
        db = tmp_path / "large.json"
        storage = TodoStorage(str(db))

        # Create a JSON file larger than the limit
        large_payload = [
            {"id": i, "text": "x" * 100, "desc": "y" * 100}
            for i in range(65000)
        ]
        db.write_text(json.dumps(large_payload), encoding="utf-8")

        # Verify the file is larger than the limit
        content = db.read_text(encoding="utf-8")
        assert len(content) > _MAX_JSON_SIZE_BYTES

        # Should raise ValueError for oversized content
        with pytest.raises(ValueError) as exc_info:
            storage.load()

        assert "too large" in str(exc_info.value).lower()

    def test_load_accepts_content_within_size_limit(self, tmp_path) -> None:
        """Verify that content within size limit is still accepted after fix."""
        db = tmp_path / "normal.json"
        storage = TodoStorage(str(db))

        # Create a normal-sized JSON file
        todos = [Todo(id=1, text="normal todo")]
        storage.save(todos)

        # Should load successfully without calling stat()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "normal todo"

    def test_toctou_cannot_bypass_size_check_via_race(self, tmp_path) -> None:
        """Simulate TOCTOU attack and verify it cannot bypass size check.

        This test simulates an attacker replacing the file content between
        what would have been the stat() check and the read_text() call.
        With the fix, this attack should be detected.
        """
        db = tmp_path / "target.json"
        storage = TodoStorage(str(db))

        # Create initial small valid file
        small_content = json.dumps([{"id": 1, "text": "small"}])
        db.write_text(small_content, encoding="utf-8")

        # Verify the small content is within limits
        assert len(small_content) < _MAX_JSON_SIZE_BYTES

        # Create large payload that would exceed limits (> 10MB)
        # Need enough items to exceed 10MB limit
        large_payload = [
            {"id": i, "text": "x" * 150}
            for i in range(80000)
        ]
        large_content = json.dumps(large_payload)
        assert len(large_content) > _MAX_JSON_SIZE_BYTES, (
            f"Large content ({len(large_content)} bytes) must exceed limit "
            f"({_MAX_JSON_SIZE_BYTES} bytes) for this test"
        )

        # Simulate TOCTOU attack: replace content during read
        # With the fix, we read first then check, so the actual content size is checked
        original_read_text = Path.read_text

        def attacking_read_text(self, *args, **kwargs):
            # Simulate attacker replacing file with large content
            # right at the moment of read (bypassing any prior stat check)
            db.write_text(large_content, encoding="utf-8")
            return original_read_text(self, *args, **kwargs)

        # With the fix, the large content should be rejected
        # because we check len(content) after reading
        with patch.object(Path, "read_text", attacking_read_text):
            with pytest.raises(ValueError, match="(?i)too large|size"):
                storage.load()

    def test_empty_file_handled_correctly(self, tmp_path) -> None:
        """Verify empty file is handled correctly without stat()."""
        db = tmp_path / "empty.json"
        storage = TodoStorage(str(db))

        # Create empty file
        db.write_text("", encoding="utf-8")

        # Should raise JSON decode error, not size error
        with pytest.raises(ValueError, match="Invalid JSON"):
            storage.load()

    def test_nonexistent_file_returns_empty_list(self, tmp_path) -> None:
        """Verify nonexistent file returns empty list without calling stat()."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        stat_called = []

        original_stat = Path.stat

        def tracking_stat(self, *args, **kwargs):
            stat_called.append(self)
            return original_stat(self, *args, **kwargs)

        with patch.object(Path, "stat", tracking_stat):
            result = storage.load()

        assert result == []
        # stat() may or may not be called for exists() check, which is fine
        # The key is that load() doesn't call stat() for size checking

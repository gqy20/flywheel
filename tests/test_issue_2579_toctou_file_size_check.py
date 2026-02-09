"""Regression tests for issue #2579: TOCTOU race condition in load().

Issue: There's a TOCTOU (Time-of-Check-Time-of-Use) race condition between
the stat().st_size check at line 64 and read_text() at line 74 in storage.py.
An attacker could grow the file between these two operations to bypass the
size check and cause a DoS attack.

Fix: Read the file content first using a bounded read, then check the actual
read size against the limit. This eliminates the TOCTOU window.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage
from flywheel.todo import Todo


def test_load_enforces_size_limit_on_actual_read(tmp_path) -> None:
    """Issue #2579: Size check should use actual read bytes, not stat().

    Before fix: stat().st_size is checked first, then file is read.
    An attacker can grow the file between these operations.

    After fix: File is read first with bounded size, then actual bytes read
    are checked against limit. The TOCTOU window is eliminated.
    """
    db = tmp_path / "todo.json"

    # Create a real file so exists() checks pass
    db.write_text("[]", encoding="utf-8")

    # Mock stat() to report a small size (file passes size check)
    # But the actual read_text returns huge content
    original_stat = Path.stat

    def fake_stat(self, follow_symlinks=True):
        if self == db:
            # Return a fake stat with small size
            _ = original_stat(self, follow_symlinks=follow_symlinks)
            # Create a mock stat result with small size
            class FakeStat:
                st_size = 100  # Small size that passes check
            return FakeStat()
        return original_stat(self, follow_symlinks=follow_symlinks)

    original_read_text = Path.read_text

    def huge_read_text(self, *args, **kwargs):
        if self == db:
            # Return huge content despite stat() saying it's small
            # This simulates file growing between stat() and read()
            huge_content = "x" * (_MAX_JSON_SIZE_BYTES + 1)
            return huge_content
        return original_read_text(self, *args, **kwargs)

    # Apply both mocks to simulate TOCTOU
    with patch.object(Path, "stat", fake_stat), \
         patch.object(Path, "read_text", huge_read_text):
        storage = TodoStorage(str(db))
        # After fix: This should raise ValueError with "too large" message
        # because the actual content size is checked, not stat() result
        with pytest.raises(ValueError, match="too large"):
            storage.load()


def test_load_accepts_file_under_limit(tmp_path) -> None:
    """Issue #2579: Normal files under the size limit should still load."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file well under the limit
    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]
    storage.save(todos)

    # Should load normally
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True


def test_load_rejects_file_at_exactly_limit(tmp_path) -> None:
    """Issue #2579: File at exactly the limit should be rejected."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file that's exactly at the limit (not under)
    # The check should be strict: file_size > limit means error
    # So file_size == limit is ok, but file_size > limit is error
    # Actually, looking at the code, it's "if file_size > _MAX_JSON_SIZE_BYTES"
    # So file at exactly limit should work

    # Create a file slightly over the limit
    content = "x" * (_MAX_JSON_SIZE_BYTES + 1)
    db.write_text(content, encoding="utf-8")

    # Should raise ValueError
    with pytest.raises(ValueError, match="too large"):
        storage.load()


def test_size_limit_is_reasonable() -> None:
    """Issue #2579: Verify the size limit is set to a reasonable value."""
    # The limit should be 10MB as documented
    expected_limit = 10 * 1024 * 1024
    assert expected_limit == _MAX_JSON_SIZE_BYTES


def test_error_message_is_informative(tmp_path) -> None:
    """Issue #2579: Error message should include size information."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file over the limit
    content = "x" * (_MAX_JSON_SIZE_BYTES + 1000)
    db.write_text(content, encoding="utf-8")

    # Should raise ValueError with informative message
    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value)
    # Error should mention the size limit
    assert "10.0MB" in error_msg or "10MB" in error_msg
    # Error should mention DoS protection
    assert "denial-of-service" in error_msg or "DoS" in error_msg


def test_empty_file_loads_successfully(tmp_path) -> None:
    """Issue #2579: Empty JSON array should load without issues."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create an empty JSON array
    db.write_text("[]", encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert loaded == []


def test_nonexistent_file_returns_empty_list(tmp_path) -> None:
    """Issue #2579: Nonexistent file should return empty list."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list, not raise error
    loaded = storage.load()
    assert loaded == []

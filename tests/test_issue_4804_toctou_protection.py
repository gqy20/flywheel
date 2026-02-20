"""Regression test for issue #4804: TOCTOU race condition in load().

This test suite verifies that the file size check in TodoStorage.load()
is not vulnerable to Time-Of-Check-Time-Of-Use (TOCTOU) attacks where
an attacker could modify the file between the stat() check and read_text().

The fix ensures a single read operation followed by size validation on
the in-memory content, eliminating the race window.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage


def test_load_uses_single_read_not_stat_then_read(tmp_path) -> None:
    """Test that load() reads content first, then checks size on in-memory data.

    This eliminates the TOCTOU race between stat() and read_text().
    We verify by mocking Path.read_text to track calls, ensuring stat()
    is not used for size checking.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small valid JSON file
    todos_data = [{"id": 1, "text": "test todo"}]
    db.write_text(json.dumps(todos_data), encoding="utf-8")

    # Track which methods are called
    stat_called = []
    original_stat = Path.stat

    def tracking_stat(self, *args, **kwargs):
        stat_called.append(self)
        return original_stat(self, *args, **kwargs)

    # Patch stat to track if it's called for size checking
    with patch.object(Path, "stat", tracking_stat):
        loaded = storage.load()

    # Verify data loaded correctly
    assert len(loaded) == 1
    assert loaded[0].id == 1
    assert loaded[0].text == "test todo"

    # The fix should NOT call stat() for size checking - it should read
    # content first and check size on the in-memory string.
    # For existing files, stat() may still be called once via exists(),
    # but NOT for size checking purposes.
    # If stat is called 2+ times (exists + size check), that indicates
    # the TOCTOU-vulnerable pattern is still in use.
    assert len(stat_called) <= 1, (
        f"stat() called {len(stat_called)} times - may indicate TOCTOU vulnerability"
    )


def test_load_rejects_content_size_over_limit_after_read(tmp_path) -> None:
    """Test that load() checks content size after reading, not via stat().

    This test creates a scenario where:
    1. File appears small initially (bypassing any stat-based check)
    2. Content is actually large (triggering content-based check)

    This simulates the TOCTOU attack where file is swapped/grows.
    """
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a large JSON payload (>10MB when encoded)
    large_payload = [{"id": i, "text": "x" * 100, "padding": "y" * 100} for i in range(65000)]
    large_content = json.dumps(large_payload)

    # Verify content is over 10MB
    content_size = len(large_content.encode("utf-8"))
    assert content_size > 10 * 1024 * 1024, f"Content size {content_size} should be > 10MB"

    # Write the large file
    db.write_text(large_content, encoding="utf-8")

    # Mock stat to report a small size (simulating TOCTOU attack)
    original_stat = Path.stat

    def fake_small_stat(self, *args, **kwargs):
        result = original_stat(self, *args, **kwargs)
        # Return a fake small size to bypass any stat-based check
        # This simulates attacker swapping file after stat() but before read()
        import stat as stat_module

        # Create a mock stat result with small size
        class FakeStatResult:
            st_size = 100  # Small size that would pass any size check
            st_mode = result.st_mode
            st_ino = result.st_ino
            st_dev = result.st_dev
            st_nlink = result.st_nlink
            st_uid = result.st_uid
            st_gid = result.st_gid
            st_atime = result.st_atime
            st_mtime = result.st_mtime
            st_ctime = result.st_ctime

        return FakeStatResult()

    with patch.object(Path, "stat", fake_small_stat):
        # Should still raise ValueError because size is checked on content,
        # not on stat() result
        with pytest.raises(ValueError, match="too large|size"):
            storage.load()


def test_load_accepts_normal_sized_content_with_fake_large_stat(tmp_path) -> None:
    """Test that normal-sized content loads even if stat reports large size.

    This verifies that the actual content size is what matters, not the
    file's stat metadata. This prevents false positives from TOCTOU in
    the other direction.
    """
    db = tmp_path / "normal.json"
    storage = TodoStorage(str(db))

    # Create a small valid JSON file
    todos_data = [{"id": 1, "text": "normal todo"}]
    small_content = json.dumps(todos_data)
    db.write_text(small_content, encoding="utf-8")

    # Mock stat to report a LARGE size (opposite of TOCTOU attack)
    original_stat = Path.stat

    def fake_large_stat(self, *args, **kwargs):
        result = original_stat(self, *args, **kwargs)

        class FakeStatResult:
            st_size = 20 * 1024 * 1024  # 20MB - would fail stat-based check
            st_mode = result.st_mode
            st_ino = result.st_ino
            st_dev = result.st_dev
            st_nlink = result.st_nlink
            st_uid = result.st_uid
            st_gid = result.st_gid
            st_atime = result.st_atime
            st_mtime = result.st_mtime
            st_ctime = result.st_ctime

        return FakeStatResult()

    # If size check is on content (not stat), this should succeed
    # because the actual content is small
    with patch.object(Path, "stat", fake_large_stat):
        # This should NOT raise if the fix is correct - content-based check
        # will see the actual small content
        loaded = storage.load()

    assert len(loaded) == 1
    assert loaded[0].text == "normal todo"

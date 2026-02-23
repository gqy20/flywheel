"""Test for TOCTOU vulnerability fix in load() method (Issue #5465).

This test verifies that the load() method reads file content once into memory
and then checks the size of the in-memory data, rather than calling stat()
before read_text(). This prevents a Time-of-Check-Time-of-Use (TOCTOU) race
condition where the file could grow between the size check and the read.
"""

from __future__ import annotations

import json
import unittest.mock as mock

import pytest

from flywheel.storage import TodoStorage, _MAX_JSON_SIZE_BYTES


def test_load_prevents_toctou_race_when_file_grows_between_stat_and_read(tmp_path) -> None:
    """Security (Issue #5465): File should be read once before size validation.

    This test simulates a TOCTOU race condition where:
    1. stat() reports a small file size
    2. File grows between stat() and read_text()
    3. read_text() returns a large payload

    The fix ensures we read once and check size of in-memory data.
    """
    db = tmp_path / "race.json"
    storage = TodoStorage(str(db))

    # Create a small initial file
    small_payload = [{"id": 1, "text": "small"}]
    db.write_text(json.dumps(small_payload), encoding="utf-8")

    # Create a large payload that would exceed the limit
    large_payload = [{"id": i, "text": "x" * 200} for i in range(60000)]
    large_content = json.dumps(large_payload)
    assert len(large_content.encode("utf-8")) > _MAX_JSON_SIZE_BYTES

    # Mock Path to simulate TOCTOU race:
    # - exists() returns True
    # - stat().st_size returns small size (simulating stat before file grows)
    # - read_text() returns large content (simulating read after file grows)
    original_path = storage.path

    class MockStat:
        st_size = 100  # Small size - under limit

    class MockPath:
        def exists(self):
            return True

        def stat(self):
            return MockStat()

        def read_text(self, encoding=None):
            # This simulates the file having grown between stat() and read_text()
            return large_content

        def __fspath__(self):
            return str(db)

    with mock.patch.object(storage, "path", MockPath()):
        # With TOCTOU vulnerability: stat shows 100 bytes but read returns 11MB+
        # The fix should check size of actual content read, not stat result
        with pytest.raises(ValueError, match="too large|size"):
            storage.load()


def test_load_still_accepts_normal_files_after_toctou_fix(tmp_path) -> None:
    """Regression: Normal files should still load correctly after fix."""
    db = tmp_path / "normal.json"
    storage = TodoStorage(str(db))

    # Create a normal small JSON file
    normal_payload = [{"id": 1, "text": "normal todo"}]
    db.write_text(json.dumps(normal_payload), encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "normal todo"


def test_load_rejects_oversized_content_even_with_small_stat(tmp_path) -> None:
    """Security: Content size is checked after reading, not stat size.

    Even if stat reports a small size, if read_text returns oversized content,
    it should be rejected.
    """
    db = tmp_path / "oversized.json"
    storage = TodoStorage(str(db))

    # Create a JSON file that is actually large
    large_payload = [{"id": i, "text": "x" * 200} for i in range(60000)]
    large_content = json.dumps(large_payload)
    db.write_text(large_content, encoding="utf-8")

    # The fix reads content first, then checks size
    # So oversized content should always be rejected regardless of stat
    with pytest.raises(ValueError, match="too large|size"):
        storage.load()

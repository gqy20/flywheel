"""Regression test for issue #2579: TOCTOU race condition in load().

This test demonstrates the Time-Of-Check-Time-Of-Use (TOCTOU) vulnerability
where a file's size is checked with stat() but then read with read_text(),
allowing an attacker to grow the file between the two operations and bypass
the size limit protection.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage


def test_toctou_vulnerability_exploit(tmp_path) -> None:
    """Demonstrate TOCTOU vulnerability: file grows between stat() and read().

    This test simulates a race condition where:
    1. stat() reports file size under the limit
    2. File grows to exceed the limit before reading content
    3. read() reads the oversized file, bypassing DoS protection

    The test should FAIL with the current implementation and PASS after fix.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid content just under the limit
    initial_todos = [{"id": i, "text": f"todo {i}"} for i in range(100)]
    initial_content = json.dumps(initial_todos, ensure_ascii=False, indent=2)
    db.write_text(initial_content, encoding="utf-8")

    # Create oversized content that exceeds the limit
    oversized_todos = [{"id": i, "text": "x" * 1000} for i in range(15000)]
    oversized_content_bytes = json.dumps(oversized_todos, ensure_ascii=False, indent=2).encode("utf-8")
    oversized_size = len(oversized_content_bytes)

    # Verify oversized content would exceed the limit
    assert oversized_size > _MAX_JSON_SIZE_BYTES

    # Mock stat to return small size, but file read returns oversized content
    # This simulates file growing between stat() and read()
    with patch.object(Path, "stat") as mock_stat:
        # stat() reports file size under the limit
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = _MAX_JSON_SIZE_BYTES // 2
        mock_stat.return_value = mock_stat_result

        # Mock the file read to return oversized content
        def oversized_open(self, *args, **kwargs):
            # Return a file-like object that returns oversized content
            mock_file = MagicMock()
            mock_file.read.return_value = oversized_content_bytes
            mock_file.__enter__ = lambda s: s
            mock_file.__exit__ = lambda s, *args: None
            return mock_file

        with patch.object(Path, "open", oversized_open), pytest.raises(ValueError, match=r"too large"):
            # Fixed code: should detect oversized read and raise ValueError
            storage.load()


def test_toctou_with_incomplete_json(tmp_path) -> None:
    """Test that incomplete oversized JSON is also rejected.

    Attackers might try to bypass by providing incomplete JSON that
    would grow to valid large JSON during parsing.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a large incomplete JSON string (exceeds limit when encoded)
    incomplete_json = '{"id": 1, "text": "' + "A" * (_MAX_JSON_SIZE_BYTES + 1000) + '"'
    incomplete_bytes = incomplete_json.encode("utf-8")
    incomplete_size = len(incomplete_bytes)

    assert incomplete_size > _MAX_JSON_SIZE_BYTES

    # Mock stat to report small size but read returns oversized content
    with patch.object(Path, "stat") as mock_stat:
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = _MAX_JSON_SIZE_BYTES // 2
        mock_stat.return_value = mock_stat_result

        def oversized_open(self, *args, **kwargs):
            mock_file = MagicMock()
            mock_file.read.return_value = incomplete_bytes
            mock_file.__enter__ = lambda s: s
            mock_file.__exit__ = lambda s, *args: None
            return mock_file

        with patch.object(Path, "open", oversized_open), pytest.raises(ValueError, match=r"too large"):
            # Should catch oversized read even before JSON parsing
            storage.load()


def test_legitimate_large_file_under_limit_still_works(tmp_path) -> None:
    """Ensure legitimate files under the limit still load correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a large but valid file under the limit
    large_todos = [{"id": i, "text": f"todo {i}"} for i in range(10000)]
    large_content = json.dumps(large_todos, ensure_ascii=False, indent=2)

    # Verify it's under the limit
    assert len(large_content.encode("utf-8")) < _MAX_JSON_SIZE_BYTES

    db.write_text(large_content, encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 10000
    assert loaded[0].text == "todo 0"
    assert loaded[9999].text == "todo 9999"


def test_size_limit_protection_without_toctou(tmp_path) -> None:
    """Test that oversized files are rejected even without TOCTOU (base case)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file that exceeds the size limit
    oversized_todos = [{"id": i, "text": "x" * 1000} for i in range(15000)]
    oversized_content = json.dumps(oversized_todos, ensure_ascii=False, indent=2)
    db.write_text(oversized_content, encoding="utf-8")

    # Should raise ValueError about file size
    with pytest.raises(ValueError, match=r"too large.*MB limit"):
        storage.load()

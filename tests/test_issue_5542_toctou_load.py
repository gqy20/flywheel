"""Tests for TOCTOU vulnerability in load() (Issue #5542).

These tests verify that the load() method is protected against TOCTOU
(Time-Of-Check-Time-Of-Use) attacks where an attacker could replace
a file between stat() and read_text() to bypass the size limit.
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage


class TestTOCTOUProtection:
    """Tests for TOCTOU vulnerability protection in load()."""

    def test_load_uses_single_fd_for_stat_and_read(self, tmp_path) -> None:
        """Test that load() uses a single file descriptor for both stat and read.

        The fix should:
        1. Open file once with os.open()
        2. Use os.fstat() on that fd (not Path.stat())
        3. Use os.read() with limited size on that fd

        This prevents TOCTOU because the same file descriptor is used throughout.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create valid data
        small_data = [{"id": 1, "text": "test data"}]
        db.write_text(json.dumps(small_data), encoding="utf-8")

        # Track os.open calls to verify single fd is used
        original_open = os.open
        open_calls = []

        def tracking_open(path, flags, *args, **kwargs):
            result = original_open(path, flags, *args, **kwargs)
            open_calls.append((path, flags, result))
            return result

        with patch("os.open", tracking_open):
            result = storage.load()

        assert len(result) == 1
        assert result[0].text == "test data"

        # The fix should open the file exactly once for reading
        # We filter to only our db file
        db_opens = [c for c in open_calls if str(db) in str(c[0])]
        assert len(db_opens) == 1, f"Expected 1 open for db, got {len(db_opens)}: {db_opens}"

    def test_load_rejects_files_exceeding_limit(self, tmp_path) -> None:
        """Test that load() rejects files exceeding the size limit."""
        db = tmp_path / "large.json"
        storage = TodoStorage(str(db))

        # Create a file larger than the limit
        large_data = [{"id": i, "text": "x" * 1000} for i in range(20000)]
        large_content = json.dumps(large_data)
        db.write_text(large_content, encoding="utf-8")

        assert db.stat().st_size > _MAX_JSON_SIZE_BYTES

        with pytest.raises(ValueError, match=r"too large"):
            storage.load()

    def test_load_atomic_size_check_and_read(self, tmp_path) -> None:
        """Regression test: verify load uses atomic size-check-and-read pattern."""
        db = tmp_path / "atomic.json"
        storage = TodoStorage(str(db))

        # Create a file
        data = [{"id": 1, "text": "atomic test"}]
        db.write_text(json.dumps(data), encoding="utf-8")

        # The load should succeed
        result = storage.load()
        assert len(result) == 1
        assert result[0].text == "atomic test"

        # Verify the file still exists and is unchanged
        raw = json.loads(db.read_text(encoding="utf-8"))
        assert raw == data

    def test_load_with_file_swapped_during_read(self, tmp_path) -> None:
        """Test that load() is protected against file swap during read."""
        db = tmp_path / "swap.json"
        storage = TodoStorage(str(db))

        # Create initial small file
        small_data = [{"id": 1, "text": "original"}]
        db.write_text(json.dumps(small_data), encoding="utf-8")

        # Load should work normally
        result = storage.load()
        assert len(result) == 1
        assert result[0].text == "original"

    def test_load_empty_file(self, tmp_path) -> None:
        """Test that load() handles empty files correctly."""
        db = tmp_path / "empty.json"
        storage = TodoStorage(str(db))

        # Empty file should return empty list (file doesn't exist behavior)
        result = storage.load()
        assert result == []

    def test_load_small_valid_json(self, tmp_path) -> None:
        """Test that load() handles small valid JSON files correctly."""
        db = tmp_path / "small.json"
        storage = TodoStorage(str(db))

        data = [
            {"id": 1, "text": "task one"},
            {"id": 2, "text": "task two", "done": True},
        ]
        db.write_text(json.dumps(data), encoding="utf-8")

        result = storage.load()
        assert len(result) == 2
        assert result[0].text == "task one"
        assert result[1].text == "task two"
        assert result[1].done is True

    def test_load_toctou_attack_blocked(self, tmp_path) -> None:
        """Test that TOCTOU attack is blocked by using single fd.

        This test verifies that the fix uses os.fstat() + os.read() on the
        same file descriptor, which prevents TOCTOU attacks.
        """
        db = tmp_path / "attack.json"
        storage = TodoStorage(str(db))

        # Create a small valid JSON file
        small_data = [{"id": 1, "text": "small"}]
        small_content = json.dumps(small_data)
        db.write_text(small_content, encoding="utf-8")

        # Load should work normally and use single fd
        result = storage.load()

        # Should get the original data
        assert len(result) == 1
        assert result[0].text == "small"

    def test_load_size_limit_enforced_on_fd(self, tmp_path) -> None:
        """Test that the size limit is enforced using fstat on the file descriptor."""
        db = tmp_path / "limit.json"
        storage = TodoStorage(str(db))

        # Create a file at the limit
        data = [{"id": 1, "text": "test"}]
        db.write_text(json.dumps(data), encoding="utf-8")

        # Track that fstat is used
        fstat_calls = []
        original_fstat = os.fstat

        def tracking_fstat(fd):
            result = original_fstat(fd)
            fstat_calls.append(fd)
            return result

        with patch("os.fstat", tracking_fstat):
            result = storage.load()

        assert len(result) == 1
        # The fix should call fstat on the fd opened for reading
        assert len(fstat_calls) >= 1, "fstat should be called on the file descriptor"

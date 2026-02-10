"""Tests for Issue #2704: load() does not handle UnicodeDecodeError.

These tests verify that TodoStorage.load() properly handles files
containing invalid UTF-8 byte sequences.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage


class TestIssue2704UTF8DecodeError:
    """Test that load() handles UnicodeDecodeError for invalid UTF-8 files."""

    def test_storage_load_handles_invalid_utf8_byte_sequence(self, tmp_path: Path) -> None:
        """Test that load() raises ValueError for invalid UTF-8 byte sequence (0xFF)."""
        # Create a file with invalid UTF-8 byte sequence
        bad_file = tmp_path / "bad_utf8.json"
        # 0xFF is not a valid UTF-8 byte
        bad_file.write_bytes(b"\xff\xff[]")

        storage = TodoStorage(str(bad_file))

        with pytest.raises(ValueError, match="Invalid UTF-8"):
            storage.load()

    def test_storage_load_handles_truncated_utf8_sequence(self, tmp_path: Path) -> None:
        """Test that load() raises ValueError for truncated/incomplete UTF-8 sequence."""
        # Create a file with truncated multi-byte UTF-8 sequence
        bad_file = tmp_path / "truncated_utf8.json"
        # 0xC2 is start of 2-byte sequence, but it's incomplete
        bad_file.write_bytes(b"\xc2")

        storage = TodoStorage(str(bad_file))

        with pytest.raises(ValueError, match="Invalid UTF-8"):
            storage.load()

    def test_storage_load_handles_mixed_valid_invalid_utf8(self, tmp_path: Path) -> None:
        """Test that load() raises ValueError for file with mixed valid/invalid UTF-8."""
        # Create a file with some valid JSON followed by invalid UTF-8
        bad_file = tmp_path / "mixed_utf8.json"
        # Valid JSON start, then invalid byte
        bad_file.write_bytes(b'["valid", "\xff"]')

        storage = TodoStorage(str(bad_file))

        with pytest.raises(ValueError, match="Invalid UTF-8"):
            storage.load()

    def test_storage_load_handles_valid_utf8(self, tmp_path: Path) -> None:
        """Test that load() still works correctly for valid UTF-8 files."""
        # Verify normal operation isn't broken
        good_file = tmp_path / "good_utf8.json"
        good_file.write_text('[]', encoding="utf-8")

        storage = TodoStorage(str(good_file))
        result = storage.load()

        assert result == []

    def test_storage_load_handles_valid_utf8_with_unicode(self, tmp_path: Path) -> None:
        """Test that load() works with valid UTF-8 containing Unicode characters."""
        # Test with various Unicode characters
        good_file = tmp_path / "unicode_utf8.json"
        good_file.write_text(
            '[{"id": 1, "text": "Hello 世界 🌍"}]',
            encoding="utf-8"
        )

        storage = TodoStorage(str(good_file))
        result = storage.load()

        assert len(result) == 1
        assert result[0].text == "Hello 世界 🌍"

"""Tests for UnicodeDecodeError handling in load() (Issue #2704).

These tests verify that:
1. Invalid UTF-8 files produce clear ValueError (not UnicodeDecodeError)
2. Error message mentions 'encoding' or 'UTF-8'
3. Various invalid UTF-8 sequences are handled
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_handles_invalid_utf8_ff_byte(tmp_path) -> None:
    """Invalid UTF-8 file (0xFF byte) should produce clear ValueError."""
    db = tmp_path / "invalid_utf8.json"
    storage = TodoStorage(str(db))

    # Create a file with invalid UTF-8 byte sequence (0xFF is invalid in UTF-8)
    db.write_bytes(b'[{"id": 1, "text": "task\xFF"}]')

    # Should raise ValueError with encoding message, not UnicodeDecodeError
    with pytest.raises(ValueError, match=r"encoding|utf-8|UTF-8"):
        storage.load()


def test_storage_load_handles_invalid_utf8_truncated_multibyte(tmp_path) -> None:
    """Truncated multi-byte UTF-8 sequence should produce clear ValueError."""
    db = tmp_path / "truncated_utf8.json"
    storage = TodoStorage(str(db))

    # Create a file with truncated multi-byte UTF-8 sequence
    # 0xC2 is start of 2-byte sequence, but missing second byte
    db.write_bytes(b'[{"id": 1, "text": "task\xC2"}]')

    # Should raise ValueError with encoding message, not UnicodeDecodeError
    with pytest.raises(ValueError, match=r"encoding|utf-8|UTF-8"):
        storage.load()


def test_storage_load_handles_invalid_utf8_overlong(tmp_path) -> None:
    """Overlong UTF-8 encoding should produce clear ValueError."""
    db = tmp_path / "overlong_utf8.json"
    storage = TodoStorage(str(db))

    # Overlong encoding for ASCII character (should be single byte)
    # 0xC0 0x80 is invalid overlong encoding for NULL
    db.write_bytes(b'[{"id": 1, "text": "task\xC0\x80"}]')

    # Should raise ValueError with encoding message, not UnicodeDecodeError
    with pytest.raises(ValueError, match=r"encoding|utf-8|UTF-8"):
        storage.load()


def test_storage_load_error_message_includes_filename(tmp_path) -> None:
    """Invalid UTF-8 error message should include the problematic filename."""
    db = tmp_path / "bad_encoding.json"
    storage = TodoStorage(str(db))

    # Create file with invalid UTF-8
    db.write_bytes(b'[{"id": 1, "text": "\xFF"}]')

    # Error message should include the filename
    with pytest.raises(ValueError, match=str(db)):
        storage.load()

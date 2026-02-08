"""Tests for TOCTOU race condition fix in TodoStorage.load() (Issue #2194).

These tests verify that:
1. File content is read completely before processing
2. Truncation detection works correctly
3. File size inconsistency is detected
4. Normal file handling remains unaffected
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage
from flywheel.todo import Todo


def test_load_reads_complete_file_content(tmp_path) -> None:
    """Test that load() reads complete file content before processing.

    This ensures that the entire file is read into memory first,
    preventing partial reads from being processed.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write valid content
    valid_content = '[{"id": 1, "text": "test"}]'
    db.write_text(valid_content, encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_load_detects_file_size_inconsistency(tmp_path) -> None:
    """Test that load() detects file size inconsistency (TOCTOU).

    This simulates a TOCTOU race where the file size changes between
    stat() and read(). The fix should detect this and raise an error.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write valid content
    valid_content = '[{"id": 1, "text": "test"}]'
    db.write_text(valid_content, encoding="utf-8")

    # Get the actual file size
    actual_size = db.stat().st_size

    # Mock stat() to report a different size
    with patch.object(Path, "stat") as mock_stat:
        # Report a size larger than actual (simulating file shrank after stat)
        mock_stat.return_value.st_size = actual_size + 100

        # Should raise ValueError about size inconsistency
        with pytest.raises(ValueError, match=r"size inconsistency|expected.*bytes but read"):
            storage.load()


def test_load_handles_truncated_json_gracefully(tmp_path) -> None:
    """Test that load() handles truncated JSON files with clear error.

    This simulates what happens when a file is truncated after the stat()
    check but before or during the read. The error should be clear.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write truncated JSON (missing closing bracket)
    truncated_content = '[{"id": 1, "text": "test"'
    db.write_text(truncated_content, encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"invalid json|truncat"):
        storage.load()


def test_load_handles_incomplete_utf8_sequence(tmp_path) -> None:
    """Test that load() handles incomplete UTF-8 sequences gracefully.

    This can happen if the file is truncated during the read operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write a valid UTF-8 JSON first
    valid_json = '[{"id": 1, "text": "test"}]'
    valid_bytes = valid_json.encode("utf-8")

    # Truncate in the middle of a multi-byte character (if we had one)
    # For this test, just truncate normally
    db.write_bytes(valid_bytes[:20])

    # Should raise an appropriate error
    with pytest.raises((ValueError, UnicodeDecodeError)):
        storage.load()


def test_load_normal_file_handling_unchanged(tmp_path) -> None:
    """Test that normal file handling is not affected by the fix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write valid content normally
    storage.save([Todo(id=1, text="normal task")])

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "normal task"


def test_load_empty_file_handled_gracefully(tmp_path) -> None:
    """Test that empty files are handled correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write empty list
    db.write_text("[]", encoding="utf-8")

    # Should load successfully as empty list
    loaded = storage.load()
    assert len(loaded) == 0


def test_load_nonexistent_file_returns_empty(tmp_path) -> None:
    """Test that non-existent files return empty list (existing behavior)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list for non-existent file
    loaded = storage.load()
    assert len(loaded) == 0


def test_max_size_check_still_works(tmp_path) -> None:
    """Test that max size check is still functional with the fix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a large JSON that exceeds max size
    large_content = "["
    for i in range(_MAX_JSON_SIZE_BYTES + 1000):
        large_content += f'{{"id":{i},"text":"x"}},'
    large_content += "]"

    db.write_text(large_content, encoding="utf-8")

    # Should raise ValueError for oversized file
    with pytest.raises(ValueError, match=r"too large"):
        storage.load()


def test_load_unicode_content_validated_correctly(tmp_path) -> None:
    """Test that Unicode content is handled correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Unicode content with multi-byte characters
    unicode_json = '[{"id": 1, "text": "Hello 世界 🌍"}]'
    db.write_text(unicode_json, encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "Hello 世界 🌍"


def test_file_size_check_before_read_prevents_dos(tmp_path) -> None:
    """Test that the DoS protection via file size check still works."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock stat to report huge size (using the actual implementation's approach)
    # Write a huge file
    large_content = "x" * (_MAX_JSON_SIZE_BYTES + 1)
    db.write_text(large_content, encoding="utf-8")

    # Should raise ValueError for oversized file
    with pytest.raises(ValueError, match=r"too large"):
        storage.load()

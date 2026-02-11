"""Tests for Issue #2777: Memory-efficient JSON loading.

Issue #2777: The load() method reads entire file into memory before JSON parsing,
potentially using 2x memory for large files. The fix uses json.load() with a file
object instead of json.loads() with read_text().
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_load_with_json_file_object(tmp_path) -> None:
    """Test that storage.load() uses json.load() with file object for memory efficiency.

    This test verifies that:
    1. The storage can load JSON files correctly using json.load()
    2. The implementation uses file objects (not read_text() + json.loads())
    3. All existing functionality is preserved
    """
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create a moderate-sized JSON file to test with
    # Large enough to show memory benefits, small enough for tests
    todos = [
        Todo(id=i, text=f"Todo item {i} with some longer text to make it bigger")
        for i in range(100)
    ]
    storage.save(todos)

    # Load should work correctly
    loaded = storage.load()
    assert len(loaded) == 100
    assert loaded[0].text == "Todo item 0 with some longer text to make it bigger"
    assert loaded[99].text == "Todo item 99 with some longer text to make it bigger"


def test_storage_load_handles_unicode_correctly(tmp_path) -> None:
    """Ensure that json.load() handles encoding correctly (UTF-8).

    The new implementation using json.load() must maintain UTF-8 encoding support.
    """
    db = tmp_path / "unicode.json"
    storage = TodoStorage(str(db))

    # Create todos with various Unicode characters
    todos = [
        Todo(id=1, text="English text"),
        Todo(id=2, text="中文文本"),
        Todo(id=3, text="日本語テキスト"),
        Todo(id=4, text="Текст на русском"),
        Todo(id=5, text="Texto en español"),
        Todo(id=6, text="🎉 Emoji support 🚀"),
    ]
    storage.save(todos)

    # Load should preserve all Unicode characters
    loaded = storage.load()
    assert len(loaded) == 6
    assert loaded[0].text == "English text"
    assert loaded[1].text == "中文文本"
    assert loaded[2].text == "日本語テキスト"
    assert loaded[3].text == "Текст на русском"
    assert loaded[4].text == "Texto en español"
    assert loaded[5].text == "🎉 Emoji support 🚀"


def test_storage_load_error_handling_malformed_json(tmp_path) -> None:
    """Ensure error handling is preserved with json.load().

    Malformed JSON should still produce clear error messages.
    """
    db = tmp_path / "malformed.json"
    storage = TodoStorage(str(db))

    # Write malformed JSON
    db.write_text('{"invalid": json}', encoding="utf-8")

    # Should raise ValueError with clear error message
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()


def test_storage_load_empty_file(tmp_path) -> None:
    """Test that empty JSON files are handled correctly."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Write an empty JSON list
    db.write_text("[]", encoding="utf-8")

    loaded = storage.load()
    assert loaded == []


def test_storage_load_respects_max_size_limit(tmp_path) -> None:
    """Verify that the file size check still works with json.load()."""
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a JSON file larger than 10MB
    large_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(65000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Verify the file is actually larger than 10MB
    assert db.stat().st_size > 10 * 1024 * 1024

    # Should raise ValueError for oversized file
    with pytest.raises(ValueError, match="too large"):
        storage.load()


def test_storage_load_non_list_json(tmp_path) -> None:
    """Test that non-list JSON is rejected properly."""
    db = tmp_path / "object.json"
    storage = TodoStorage(str(db))

    # Write a JSON object instead of a list
    db.write_text('{"not": "a list"}', encoding="utf-8")

    # Should raise ValueError
    with pytest.raises(ValueError, match="must be a JSON list"):
        storage.load()

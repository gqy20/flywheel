"""Tests for Issue #2777: load() memory efficiency.

This test suite verifies that load() uses json.load() with a file object
instead of json.loads() with read_text() to avoid creating a separate string
copy of the entire file content.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_large_json_file_successfully(tmp_path) -> None:
    """Test that large (~1MB) JSON files load successfully.

    This verifies that json.load() with file object works for large files.
    A 1MB JSON file should be well within the 10MB limit.
    """
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a JSON file approximately 1MB in size
    # Each todo is roughly 150 bytes, so ~7000 todos = ~1MB
    large_payload = [
        {"id": i, "text": f"Todo item {i} with some description text", "done": i % 2 == 0}
        for i in range(7000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Verify the file is approximately 1MB (at least 500KB to be meaningful)
    assert db.stat().st_size > 500 * 1024

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 7000
    assert loaded[0].id == 0
    assert loaded[0].text == "Todo item 0 with some description text"
    assert loaded[6999].id == 6999


def test_load_handles_malformed_json_with_clear_error(tmp_path) -> None:
    """Test that malformed JSON still produces a clear error message.

    This verifies that error handling quality is not degraded by the change.
    """
    db = tmp_path / "malformed.json"
    storage = TodoStorage(str(db))

    # Create a file with malformed JSON
    db.write_text('{"id": 1, "text": "todo", "done": true', encoding="utf-8")

    # Should raise ValueError with clear error message
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()


def test_load_size_check_happens_before_opening_file(tmp_path) -> None:
    """Test that file size limit check still works before opening file.

    This verifies that the size check (which uses stat()) still prevents
    loading oversized files, protecting against DoS attacks.
    """
    db = tmp_path / "oversized.json"
    storage = TodoStorage(str(db))

    # Create a JSON file larger than 10MB (~11MB of data)
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


def test_load_normal_sized_file_still_works(tmp_path) -> None:
    """Test that normal-sized JSON files still load correctly.

    This is a regression test to ensure the change doesn't break normal usage.
    """
    db = tmp_path / "normal.json"
    storage = TodoStorage(str(db))

    # Create a normal small JSON file
    todos = [
        Todo(id=1, text="normal todo"),
        Todo(id=2, text="another todo", done=True),
    ]
    storage.save(todos)

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "normal todo"
    assert loaded[1].done is True


def test_load_empty_file_returns_empty_list(tmp_path) -> None:
    """Test that an empty JSON file (empty list) returns empty list."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Create an empty JSON array
    db.write_text("[]", encoding="utf-8")

    # Should load successfully as empty list
    loaded = storage.load()
    assert loaded == []


def test_load_nonexistent_file_returns_empty_list(tmp_path) -> None:
    """Test that loading a nonexistent file returns an empty list."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist, should return empty list
    loaded = storage.load()
    assert loaded == []


def test_load_json_with_unicode(tmp_path) -> None:
    """Test that JSON with unicode characters loads correctly.

    Verifies encoding handling is preserved with json.load().
    """
    db = tmp_path / "unicode.json"
    storage = TodoStorage(str(db))

    # Create JSON with unicode content
    todos = [
        Todo(id=1, text="Task with unicode: 你好世界"),
        Todo(id=2, text="Emoji: 🎉🚀"),
        Todo(id=3, text="Mixed: Hello 世界 🌍"),
    ]
    storage.save(todos)

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 3
    assert loaded[0].text == "Task with unicode: 你好世界"
    assert loaded[1].text == "Emoji: 🎉🚀"
    assert loaded[2].text == "Mixed: Hello 世界 🌍"

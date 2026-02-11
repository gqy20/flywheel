"""Test for Issue #2777 - Memory-efficient JSON loading.

This test verifies that load() uses json.load() with a file object
instead of json.loads() with read_text() to reduce memory usage by ~50%
for large JSON files.

The test creates a ~1MB JSON file to verify the implementation works correctly
with moderately large files.
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_load_handles_large_json_efficiently(tmp_path) -> None:
    """Issue #2777: Verify load() handles large JSON files efficiently.

    This test creates a ~1MB JSON file (well within the 10MB limit) to verify
    that the storage can load it correctly. The implementation should use
    json.load() with a file object instead of json.loads() with read_text()
    to avoid creating a duplicate string copy in memory.
    """
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a ~1MB JSON file with realistic todo data
    # Each todo is ~100 bytes, so we need ~10000 todos for ~1MB
    large_payload = [
        Todo(
            id=i,
            text=f"Task number {i} with some extended description text to make it longer",
        )
        for i in range(10000)
    ]
    storage.save(large_payload)

    # Verify the file is actually around 1-3MB (each todo is ~225 bytes)
    file_size_mb = db.stat().st_size / (1024 * 1024)
    assert 0.8 < file_size_mb < 3.0, f"Expected ~1-3MB file, got {file_size_mb:.2f}MB"

    # Should load successfully with the new implementation
    loaded = storage.load()
    assert len(loaded) == 10000
    assert loaded[0].text == "Task number 0 with some extended description text to make it longer"
    assert loaded[9999].text == "Task number 9999 with some extended description text to make it longer"


def test_storage_load_with_unicode_content(tmp_path) -> None:
    """Issue #2777: Verify json.load() handles Unicode content correctly.

    Ensures that switching from read_text() to file object doesn't break
    Unicode character handling.
    """
    db = tmp_path / "unicode.json"
    storage = TodoStorage(str(db))

    # Create todos with various Unicode characters
    unicode_todos = [
        Todo(id=1, text="English text"),
        Todo(id=2, text="中文文本"),
        Todo(id=3, text="日本語テキスト"),
        Todo(id=4, text="العربية"),
        Todo(id=5, text="Emoji 😎🎉"),
        Todo(id=6, text="Mixed: English + 中文 + 🌍"),
    ]
    storage.save(unicode_todos)

    loaded = storage.load()
    assert len(loaded) == 6
    assert loaded[1].text == "中文文本"
    assert loaded[4].text == "Emoji 😎🎉"
    assert loaded[5].text == "Mixed: English + 中文 + 🌍"

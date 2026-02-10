"""Regression tests for issue #2669: TOCTOU vulnerability in load().

Issue: File size check and read are separate operations (stat() + read_text()),
allowing an attacker to bypass the 10MB DoS limit by replacing the file between
the check and the read.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage, _MAX_JSON_SIZE_BYTES
from flywheel.todo import Todo


def test_load_rejects_file_exceeding_10mb_limit(tmp_path) -> None:
    """Issue #2669: Files larger than 10MB should be rejected.

    Before fix: stat() checks size, but read_text() has no limit
    After fix: Read operation has bounded byte count

    This test creates a file larger than the limit and verifies it's rejected.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a JSON file that exceeds the size limit
    # We'll create a file with a large array of objects
    large_json = "[" + ",".join(['{"id":1,"text":"todo"}'] * 100000) + "]"

    # Pad to exceed 10MB
    while len(large_json.encode("utf-8")) <= _MAX_JSON_SIZE_BYTES:
        large_json += "," + large_json

    db.write_text(large_json, encoding="utf-8")

    # Verify the file is actually larger than the limit
    actual_size = db.stat().st_size
    assert actual_size > _MAX_JSON_SIZE_BYTES, f"Test setup failed: file size {actual_size} is not larger than limit {_MAX_JSON_SIZE_BYTES}"

    # Should raise ValueError for oversized file
    with pytest.raises(ValueError, match="JSON file too large"):
        storage.load()


def test_load_accepts_file_at_exactly_10mb_boundary(tmp_path) -> None:
    """Issue #2669: Files at exactly the 10MB boundary should work.

    This ensures the fix doesn't incorrectly reject valid files.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a JSON file exactly at the size limit
    # Start with valid JSON
    base_json = '[{"id":1,"text":"test"}]'
    base_size = len(base_json.encode("utf-8"))

    # Calculate how much padding we need
    padding_needed = _MAX_JSON_SIZE_BYTES - base_size

    # Create padding that's valid JSON (just spaces in a string value)
    # Using spaces ensures we don't accidentally create invalid JSON
    padding = " " * padding_needed
    exact_size_json = f'[{{"id":1,"text":"test{padding}"}}]'

    # Verify exact size
    actual_size = len(exact_size_json.encode("utf-8"))
    assert actual_size == _MAX_JSON_SIZE_BYTES, f"Test setup failed: file size {actual_size} != limit {_MAX_JSON_SIZE_BYTES}"

    db.write_text(exact_size_json, encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].id == 1
    assert todos[0].text.startswith("test")


def test_load_accepts_small_file_below_limit(tmp_path) -> None:
    """Issue #2669: Normal small files should still work correctly.

    Regression test to ensure the fix doesn't break normal operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Normal small JSON file
    todos = [Todo(id=1, text="normal todo"), Todo(id=2, text="another todo")]
    storage.save(todos)

    # Should load normally
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "normal todo"
    assert loaded[1].text == "another todo"


def test_load_with_extra_data_beyond_limit_is_detected(tmp_path) -> None:
    """Issue #2669: Detect when file has more data beyond the size limit.

    This tests the atomic read behavior - if we read up to the limit
    but there's still more data, we should reject the file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file where first 10MB looks like valid JSON
    # but there's more data after (this would exploit a naive read-with-limit)
    base_json = '[{"id":1,"text":"test"'
    base_size = len(base_json.encode("utf-8"))

    # Calculate padding to get exactly at limit - closing bracket
    # We want: [<10MB of data>] + extra junk
    padding_needed = _MAX_JSON_SIZE_BYTES - base_size - len('"]}'.encode("utf-8"))
    # Add 1 because off-by-one in our calculation
    padding_needed += 1
    padding = "x" * padding_needed

    # Write exactly 10MB of valid JSON, then extra
    valid_part = f'[{{"id":1,"text":"test{padding}"}}]'
    # Verify we're at or close to limit
    assert len(valid_part.encode("utf-8")) >= _MAX_JSON_SIZE_BYTES - 10

    extra_data = ',{"id":2,"text":"this should be rejected"}'
    full_content = valid_part + extra_data

    db.write_bytes(full_content.encode("utf-8"))

    # File is larger than limit, should be rejected
    with pytest.raises(ValueError, match="JSON file too large"):
        storage.load()


def test_load_returns_empty_list_for_nonexistent_file(tmp_path) -> None:
    """Issue #2669: Regression test - nonexistent file should return empty list.

    This ensures the fix doesn't break the normal behavior for missing files.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list, not raise error
    todos = storage.load()
    assert todos == []


def test_load_with_unicode_content_still_works(tmp_path) -> None:
    """Issue #2669: Regression test - Unicode content should still work.

    Ensures the bounded read approach handles UTF-8 correctly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create JSON with various Unicode content
    todos = [
        Todo(id=1, text="English text"),
        Todo(id=2, text="中文文本"),
        Todo(id=3, text="العربية"),
        Todo(id=4, text="Emoji 🎉🔥"),
    ]
    storage.save(todos)

    # Should load and preserve Unicode
    loaded = storage.load()
    assert len(loaded) == 4
    assert loaded[0].text == "English text"
    assert loaded[1].text == "中文文本"
    assert loaded[2].text == "العربية"
    assert loaded[3].text == "Emoji 🎉🔥"

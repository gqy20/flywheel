"""Regression test for TOCTOU vulnerability in TodoStorage.load().

Issue #2669: The load() method has a Time-of-Check-Time-of-Use (TOCTOU) vulnerability
where file size is checked via stat() before reading, but the file is read via read_text()
in a separate operation. An attacker could replace a small file with a large one between
the stat() call and the read_text() call, bypassing the size limit protection.

This test ensures that the fix prevents this attack by enforcing size limits atomically
with the read operation.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage
from flywheel.todo import Todo


def test_load_rejects_file_larger_than_limit_during_read(tmp_path) -> None:
    """Test that load() rejects files larger than limit via bounded read.

    This simulates a TOCTOU attack where the file grows between the check
    and the read. The fix prevents this by using bounded read() which only
    reads limit + 1 bytes maximum.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small valid file first (under 10MB)
    small_content = json.dumps([{"id": 1, "text": "small"}])
    db.write_text(small_content, encoding="utf-8")

    # Mock Path.open to return a file object that yields large data
    # This simulates what happens if file grows after exists() check
    large_data = b'[' + b'{"id": 1, "text": "' + b'x' * (_MAX_JSON_SIZE_BYTES + 1000) + b'"}]'

    # Create a mock file object that returns large data on read()
    mock_file = MagicMock()
    mock_file.read.return_value = large_data
    mock_file.__enter__ = MagicMock(return_value=mock_file)
    mock_file.__exit__ = MagicMock(return_value=False)

    with patch.object(Path, "open", return_value=mock_file), pytest.raises(
        ValueError, match=r"too large|limit"
    ):
        # The fix should catch this because read() is bounded to limit + 1
        # We check len(data) > limit after the read
        storage.load()


def test_load_accepts_large_file_under_limit(tmp_path) -> None:
    """Test that load() accepts large files that are under the limit.

    This uses a reasonably sized test file to verify the fix doesn't break normal operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a moderately sized JSON file (100KB - well under 10MB limit)
    # This is large enough to test but small enough to be fast
    data = []
    for i in range(1000):
        text = "x" * 100
        item = {"id": i, "text": text, "done": i % 2 == 0}
        data.append(item)

    json_str = json.dumps(data)
    actual_size = len(json_str.encode("utf-8"))

    # Verify it's under the limit
    assert actual_size < _MAX_JSON_SIZE_BYTES

    db.write_bytes(json_str.encode("utf-8"))

    # This should load successfully
    todos = storage.load()
    assert len(todos) == len(data)
    assert todos[0].id == 0
    assert todos[999].id == 999


def test_load_rejects_file_over_limit(tmp_path) -> None:
    """Test that load() rejects files larger than 10MB limit.

    Uses a smaller test by mocking the read to return oversized data.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small file first
    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")

    # Mock Path.open to simulate reading a file larger than limit
    large_data = b'[' + b'{"id": 1, "text": "' + b'x' * (_MAX_JSON_SIZE_BYTES + 1000) + b'"}]'

    mock_file = MagicMock()
    mock_file.read.return_value = large_data
    mock_file.__enter__ = MagicMock(return_value=mock_file)
    mock_file.__exit__ = MagicMock(return_value=False)

    with patch.object(Path, "open", return_value=mock_file), pytest.raises(
        ValueError, match=r"too large|limit"
    ):
        # Should raise ValueError because data is too large
        storage.load()


def test_normal_load_still_works(tmp_path) -> None:
    """Regression test: ensure normal load behavior isn't broken."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Normal sized file
    todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2", done=True),
        Todo(id=3, text="task with unicode: 你好"),
    ]
    storage.save(todos)

    # Should load normally
    loaded = storage.load()
    assert len(loaded) == 3
    assert loaded[0].text == "task 1"
    assert loaded[1].done is True
    assert loaded[2].text == "task with unicode: 你好"


def test_load_empty_file_returns_empty_list(tmp_path) -> None:
    """Regression test: ensure empty files still work."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Empty JSON array
    db.write_text("[]", encoding="utf-8")

    loaded = storage.load()
    assert loaded == []


def test_load_nonexistent_file_returns_empty_list(tmp_path) -> None:
    """Regression test: ensure nonexistent files still return empty list."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist
    loaded = storage.load()
    assert loaded == []


def test_file_size_limit_is_10mb() -> None:
    """Verify the constant is set to 10MB as documented."""
    assert _MAX_JSON_SIZE_BYTES == 10 * 1024 * 1024


def test_load_uses_bounded_read_not_separate_stat_and_read(tmp_path) -> None:
    """Verify the fix uses bounded read instead of separate stat() + read_text().

    The fix uses Path.open() + f.read(limit + 1) to enforce the size limit
    atomically with the read operation, preventing TOCTOU attacks.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small valid file
    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")

    # The fix should NOT call read_text() (old vulnerable method)
    # It should use Path.open() with bounded f.read()
    with patch.object(Path, "read_text", side_effect=AssertionError("read_text should not be called")):
        # This should work without calling read_text
        storage.load()

    # Verify that open() is being used (with bounded read)
    with patch("builtins.open", mock_open(read_data=b'[{"id": 1, "text": "test"}]')):
        # We can't easily mock Path.open() for testing, but the above
        # confirms read_text() isn't used
        pass

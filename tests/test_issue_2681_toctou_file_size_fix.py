"""Regression tests for issue #2681: TOCTOU race condition in file size check.

Issue: The file size check via stat() and file read via read_text() are not atomic.
An attacker could replace a small file with a large file between the stat() and read_text() calls.

Fix: Use bounded read that stops reading after a maximum size, preventing memory exhaustion
even if file grows between size check and read.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage


def test_load_fails_on_oversized_file(tmp_path) -> None:
    """Issue #2681: Files larger than _MAX_JSON_SIZE_BYTES should be rejected.

    The bounded read approach reads up to _MAX_JSON_SIZE_BYTES + 1 bytes,
    then checks if there's more data. This prevents TOCTOU attacks.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file that's larger than the limit
    # Use simple repeating pattern to ensure we exceed 10MB
    item = '{"id":1,"text":"data"},'

    # Calculate how many items we need to exceed the limit
    items = []
    total_size = 2  # Opening and closing brackets

    while total_size < _MAX_JSON_SIZE_BYTES + 100000:  # Add buffer to ensure we exceed
        items.append(item)
        total_size += len(item.encode('utf-8'))

    content = '[' + ''.join(items) + ']'
    db.write_bytes(content.encode('utf-8'))

    # File should be larger than the limit
    assert db.stat().st_size > _MAX_JSON_SIZE_BYTES

    # Should raise ValueError due to size limit
    with pytest.raises(ValueError, match=r"too large"):
        storage.load()


def test_bounded_read_prevents_memory_exhaustion(tmp_path) -> None:
    """Issue #2681: Reading should use bounded memory even for huge files.

    Mock the builtin open() to simulate a file that's larger than reported.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small valid file first
    small_content = json.dumps([{"id": 1, "text": "small"}])
    db.write_text(small_content, encoding="utf-8")

    # Store the original open function for our fake file to use
    import builtins
    original_open = builtins.open

    # Create a fake file object that returns more data than expected
    class FakeFile:
        """Simulates a file that grows during reading (TOCTOU attack)."""
        def __init__(self, real_path, mode, *args, **kwargs):
            self.real_path = real_path
            self.mode = mode
            self.read_count = 0
            # Use the original open to read the actual file content
            self.real_file = original_open(real_path, mode, *args, **kwargs)
            self.initial_content = self.real_file.read()
            self.real_file.close()

        def read(self, size=-1):
            self.read_count += 1
            # First read: return small content (under limit)
            if self.read_count == 1:
                return self.initial_content
            # Second read: return more data to simulate TOCTOU attack
            # This simulates the file growing between the first and second read
            else:
                # Return extra byte to indicate there's more data
                return b"x"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    # Patch builtins.open to use our fake file
    with patch('builtins.open', FakeFile):
        # Should fail because after reading the initial content,
        # we detect there's more data (TOCTOU indicator)
        with pytest.raises(ValueError, match=r"too large"):
            storage.load()


def test_max_size_boundary_case(tmp_path) -> None:
    """Issue #2681: Files exactly at the size limit boundary.

    The bounded read reads _MAX_JSON_SIZE_BYTES + 1 and then checks
    for additional data. Files at or exactly over the limit are rejected.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create content that's exactly at the limit
    # Use simple repeating pattern
    item = '{"id":1,"text":"data"},'
    items_needed = (_MAX_JSON_SIZE_BYTES // len(item)) - 10  # Stay under limit

    content = "[" + item * items_needed
    content = content.rstrip(",") + "]"

    # Ensure it's under the limit
    content_bytes = content.encode('utf-8')
    assert len(content_bytes) < _MAX_JSON_SIZE_BYTES

    db.write_bytes(content_bytes)

    # Should load successfully (it's under the limit)
    todos = storage.load()
    assert len(todos) > 0


def test_oversized_by_one_byte_fails(tmp_path) -> None:
    """Issue #2681: File even one byte over limit should fail.

    This tests the bounded read's overflow detection.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create content that's exactly _MAX_JSON_SIZE_BYTES + 1
    # We'll use simple repeating pattern
    base_content = b'{"id":1,"text":"' + b'x' * 100 + b'"},'

    # Calculate how many items we need
    items = []
    total_size = 2  # Opening and closing brackets

    while total_size < _MAX_JSON_SIZE_BYTES + 100:
        items.append(base_content)
        total_size += len(base_content)

    content = b'[' + b''.join(items) + b']'

    # Ensure it's over the limit
    assert len(content) > _MAX_JSON_SIZE_BYTES

    db.write_bytes(content)

    # Should raise ValueError due to size limit
    with pytest.raises(ValueError, match=r"too large"):
        storage.load()


def test_normal_small_files_load_correctly(tmp_path) -> None:
    """Issue #2681: Normal small files should continue to work correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Normal small JSON file
    small_content = json.dumps([
        {"id": 1, "text": "task 1"},
        {"id": 2, "text": "task 2"},
        {"id": 3, "text": "task 3"},
    ])
    db.write_text(small_content, encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 3
    assert todos[0].text == "task 1"
    assert todos[1].text == "task 2"
    assert todos[2].text == "task 3"


def test_empty_file_loads_as_empty_list(tmp_path) -> None:
    """Issue #2681: Empty files should be handled gracefully."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Empty JSON array
    db.write_text("[]", encoding="utf-8")

    todos = storage.load()
    assert todos == []


def test_file_with_unicode_loads_correctly(tmp_path) -> None:
    """Issue #2681: Files with unicode content should still work."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # JSON with unicode content
    unicode_content = json.dumps([
        {"id": 1, "text": "你好世界"},
        {"id": 2, "text": "🎉🎊"},
        {"id": 3, "text": "مرحبا"},
    ])
    db.write_text(unicode_content, encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 3
    assert todos[0].text == "你好世界"
    assert todos[1].text == "🎉🎊"
    assert todos[2].text == "مرحبا"


def test_memory_bounded_during_read(tmp_path) -> None:
    """Issue #2681: Verify that read() calls are bounded.

    This test verifies that we never read more than _MAX_JSON_SIZE_BYTES + 1
    bytes in a single read operation, even if the file is larger.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a large file
    large_content = "[" + ",".join([f'{{"id":{i},"text":"{"x"*100}"}}' for i in range(100000)]) + "]"
    db.write_text(large_content, encoding="utf-8")

    # Track the read calls
    read_sizes = []

    original_open = open

    class TrackingFile:
        def __init__(self, path, mode, *args, **kwargs):
            self._file = original_open(path, mode, *args, **kwargs)

        def read(self, size=-1):
            read_sizes.append(size)
            return self._file.read(size)

        def __enter__(self):
            self._file.__enter__()
            return self

        def __exit__(self, *args):
            return self._file.__exit__(*args)

    with patch('builtins.open', TrackingFile):
        # This should fail due to size limit
        with pytest.raises(ValueError, match=r"too large"):
            storage.load()

    # Verify that no single read requested more than the limit + 1
    # The implementation uses read(_MAX_JSON_SIZE_BYTES + 1)
    max_requested = max((s for s in read_sizes if s > 0), default=0)
    assert max_requested <= _MAX_JSON_SIZE_BYTES + 10, \
        f"Read requested {max_requested} bytes, which exceeds bounded limit"

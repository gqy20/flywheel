"""Tests for load() caching mechanism (issue #6436).

This test suite verifies that TodoStorage.load() implements mtime-based caching
to avoid unnecessary file reads when the file hasn't changed.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_uses_cache_on_repeated_calls(tmp_path: Path) -> None:
    """Test that repeated load() calls use cached data without file re-read."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="cached todo")]
    storage.save(todos)

    # First load should read file
    result1 = storage.load()
    assert len(result1) == 1

    # Track file reads
    read_count = 0
    original_read_text = Path.read_text

    def counting_read_text(self, *args, **kwargs):
        nonlocal read_count
        read_count += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", counting_read_text):
        # Second load should use cache (no file read)
        result2 = storage.load()
        assert read_count == 0, "load() should use cache without reading file"
        assert len(result2) == 1
        assert result2[0].text == "cached todo"


def test_cache_invalidated_on_mtime_change(tmp_path: Path) -> None:
    """Test that cache is invalidated when file mtime changes."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="original")]
    storage.save(todos)

    # First load to populate cache
    result1 = storage.load()
    assert result1[0].text == "original"

    # Modify file externally (simulating another process)
    # Need to ensure mtime changes
    time.sleep(0.01)  # Ensure different timestamp
    new_todos = [Todo(id=1, text="modified")]
    storage.save(new_todos)

    # Second load should detect mtime change and re-read
    result2 = storage.load()
    assert result2[0].text == "modified", "load() should detect file change"


def test_cache_invalidated_after_save(tmp_path: Path) -> None:
    """Test that cache is invalidated after save() operation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # First load to populate cache
    result1 = storage.load()
    assert len(result1) == 1

    # Save new data (should invalidate cache)
    new_todos = [Todo(id=1, text="updated"), Todo(id=2, text="new")]
    storage.save(new_todos)

    # Load should return updated data (not cached)
    result2 = storage.load()
    assert len(result2) == 2
    assert result2[0].text == "updated"
    assert result2[1].text == "new"


def test_load_performance_with_caching(tmp_path: Path) -> None:
    """Performance test: multiple loads should be faster with caching."""
    import json

    db = tmp_path / "todo.json"

    # Create a larger dataset to make file reads noticeable
    large_todos = [Todo(id=i, text=f"todo item {i}" * 10) for i in range(100)]

    # Write directly to file
    payload = [todo.to_dict() for todo in large_todos]
    db.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    storage = TodoStorage(str(db))

    # Track how many times the file is actually read
    read_count = 0
    original_read_text = Path.read_text

    def counting_read_text(self, *args, **kwargs):
        nonlocal read_count
        read_count += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", counting_read_text):
        # Multiple loads
        for _ in range(10):
            result = storage.load()
            assert len(result) == 100

        # With caching, only 1 file read should occur
        # (first load reads, subsequent use cache)
        assert read_count == 1, (
            f"Expected 1 file read with caching, got {read_count}"
        )


def test_different_storage_instances_have_separate_caches(tmp_path: Path) -> None:
    """Test that different storage instances maintain separate caches."""
    db = tmp_path / "todo.json"

    # Create initial data
    storage1 = TodoStorage(str(db))
    todos = [Todo(id=1, text="shared")]
    storage1.save(todos)

    # Load with first instance (populates its cache)
    result1 = storage1.load()
    assert len(result1) == 1

    # Create second instance
    storage2 = TodoStorage(str(db))

    # Second instance should still work (has its own cache state)
    result2 = storage2.load()
    assert len(result2) == 1
    assert result2[0].text == "shared"


def test_cache_cleared_when_file_deleted(tmp_path: Path) -> None:
    """Test that cache handles file deletion correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and load data
    todos = [Todo(id=1, text="to be deleted")]
    storage.save(todos)
    result1 = storage.load()
    assert len(result1) == 1

    # Delete file
    db.unlink()

    # Load should return empty list (not cached data)
    result2 = storage.load()
    assert result2 == [], "load() should return empty list after file deletion"

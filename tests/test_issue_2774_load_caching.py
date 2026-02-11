"""Tests for load() caching mechanism in TodoStorage.

Issue: #2774 - Add load() method caching to improve performance by reducing
repeated file I/O operations.

This test suite verifies:
1. Cache is used on subsequent load() calls
2. save() updates the cache
3. invalidate_cache() forces reload on next load()
4. Cache can be disabled via enable_cache parameter
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_uses_cache_on_second_call(tmp_path) -> None:
    """Test that two consecutive load() calls only read the file once."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2")]
    storage.save(todos)

    # First load - should read from file
    first_result = storage.load()
    assert len(first_result) == 2
    assert first_result[0].text == "task1"

    # Track if Path.read_text is called during second load
    original_read_text = Path.read_text
    read_text_call_count = 0

    def tracked_read_text(self, *args, **kwargs):
        nonlocal read_text_call_count
        read_text_call_count += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", tracked_read_text):
        # Second load - should use cache (no file read)
        second_result = storage.load()
        assert len(second_result) == 2
        assert second_result[0].text == "task1"
        # Verify read_text was not called (cache was used)
        assert read_text_call_count == 0, "Second load should use cache, not read file"


def test_save_updates_cache(tmp_path) -> None:
    """Test that save() updates the cache with new data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initial save
    todos = [Todo(id=1, text="original")]
    storage.save(todos)

    # Load to populate cache
    loaded = storage.load()
    assert loaded[0].text == "original"

    # Modify and save
    modified = [Todo(id=1, text="modified"), Todo(id=2, text="new")]
    storage.save(modified)

    # Track if Path.read_text is called during load after save
    original_read_text = Path.read_text
    read_text_call_count = 0

    def tracked_read_text(self, *args, **kwargs):
        nonlocal read_text_call_count
        read_text_call_count += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", tracked_read_text):
        # Load after save - should use updated cache (no file read)
        result = storage.load()
        assert len(result) == 2
        assert result[0].text == "modified"
        assert result[1].text == "new"
        # Verify read_text was not called (cache was updated by save)
        assert read_text_call_count == 0, "Load after save should use updated cache"


def test_invalidate_cache_forces_reload(tmp_path) -> None:
    """Test that invalidate_cache() forces next load() to re-read file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initial data
    todos = [Todo(id=1, text="cached")]
    storage.save(todos)

    # First load - populates cache
    first = storage.load()
    assert first[0].text == "cached"

    # Manually modify file to simulate external change
    db.write_text('[{"id": 1, "text": "external-modified", "done": false}]', encoding="utf-8")

    # Invalidate cache
    storage.invalidate_cache()

    # Load after invalidate - should re-read file
    second = storage.load()
    assert second[0].text == "external-modified", "Should reload from file after invalidate"


def test_cache_disabled_when_enable_cache_false(tmp_path) -> None:
    """Test that caching is disabled when enable_cache=False."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_cache=False)

    # Create initial data
    todos = [Todo(id=1, text="task1")]
    storage.save(todos)

    # Track read_text calls for first load
    original_read_text = Path.read_text
    read_text_call_count_1 = 0

    def tracked_read_text_1(self, *args, **kwargs):
        nonlocal read_text_call_count_1
        read_text_call_count_1 += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", tracked_read_text_1):
        # First load - should read from file
        first = storage.load()
        assert first[0].text == "task1"
        assert read_text_call_count_1 == 1, "First load should read file"

    # Track read_text calls for second load (separate counter)
    read_text_call_count_2 = 0

    def tracked_read_text_2(self, *args, **kwargs):
        nonlocal read_text_call_count_2
        read_text_call_count_2 += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", tracked_read_text_2):
        # Second load - should also read from file (cache disabled)
        second = storage.load()
        assert second[0].text == "task1"
        assert read_text_call_count_2 == 1, "Second load should also read file when cache disabled"


def test_cache_enabled_by_default(tmp_path) -> None:
    """Test that caching is enabled by default (backward compatibility)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))  # No enable_cache parameter

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Invalidate cache after save to force reload for testing
    storage.invalidate_cache()

    # Track read_text calls for first load
    original_read_text = Path.read_text
    read_text_call_count_1 = 0

    def tracked_read_text_1(self, *args, **kwargs):
        nonlocal read_text_call_count_1
        read_text_call_count_1 += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", tracked_read_text_1):
        # First load - should read from file
        storage.load()
        assert read_text_call_count_1 == 1, "First load should read file"

    # Track read_text calls for second load (separate counter)
    read_text_call_count_2 = 0

    def tracked_read_text_2(self, *args, **kwargs):
        nonlocal read_text_call_count_2
        read_text_call_count_2 += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", tracked_read_text_2):
        # Second load - should use cache (default behavior)
        storage.load()
        assert read_text_call_count_2 == 0, "Second load should use cache by default"


def test_invalid_cache_after_save_to_different_file(tmp_path) -> None:
    """Test cache isolation when multiple storage instances write to same file."""
    db = tmp_path / "shared.json"

    storage1 = TodoStorage(str(db))
    storage2 = TodoStorage(str(db))

    # storage1 saves data
    todos1 = [Todo(id=1, text="from-storage1")]
    storage1.save(todos1)

    # storage2 loads and gets cached data
    loaded1 = storage2.load()
    assert loaded1[0].text == "from-storage1"

    # storage1 modifies data (different storage instance)
    todos2 = [Todo(id=1, text="modified-by-storage1")]
    storage1.save(todos2)

    # storage2 has stale cache - invalidate to get fresh data
    storage2.invalidate_cache()
    loaded2 = storage2.load()
    assert loaded2[0].text == "modified-by-storage1"

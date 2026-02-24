"""Regression tests for issue #5469: Add load cache with invalidation.

This test suite verifies that TodoStorage.load() caches data to reduce
repeated IO, with proper invalidation based on file modification time.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_returns_cached_data_when_file_unchanged(tmp_path) -> None:
    """Test that consecutive load() calls return cached data without re-reading file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # First load - should read from file
    first_load = storage.load()

    # Track file reads: second load should use cache, not re-read file
    original_read_text = Path.read_text
    read_count = [0]

    def tracking_read_text(self, *args, **kwargs):
        read_count[0] += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", tracking_read_text):
        second_load = storage.load()

    # Second load should NOT have read the file (used cache)
    assert read_count[0] == 0, "Second load should use cache, not re-read file"

    # Data should be identical
    assert len(second_load) == 1
    assert second_load[0].text == "initial"
    assert first_load[0].text == second_load[0].text


def test_load_refreshes_cache_when_file_modified_externally(tmp_path) -> None:
    """Test that load() detects external file modifications and returns new data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # First load - cache the data
    first_load = storage.load()
    assert first_load[0].text == "initial"

    # Modify file externally (bypassing TodoStorage)
    # Need to ensure mtime changes - add a tiny delay
    time.sleep(0.01)
    new_data = [{"id": 1, "text": "externally modified", "done": True}]
    db.write_text(json.dumps(new_data), encoding="utf-8")

    # Second load - should detect mtime change and re-read
    second_load = storage.load()
    assert second_load[0].text == "externally modified"
    assert second_load[0].done is True


def test_save_updates_cache(tmp_path) -> None:
    """Test that save() updates the cache automatically."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Load to populate cache
    first_load = storage.load()
    assert first_load[0].text == "initial"

    # Save new data - this should update the cache
    new_todos = [Todo(id=1, text="updated"), Todo(id=2, text="new")]
    storage.save(new_todos)

    # Load immediately after save should return cached data (no file re-read)
    original_read_text = Path.read_text
    read_count = [0]

    def tracking_read_text(self, *args, **kwargs):
        read_count[0] += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", tracking_read_text):
        cached_load = storage.load()

    # Should use cache (updated by save), not re-read file
    assert read_count[0] == 0, "Load after save should use cache"

    # Data should match what was saved
    assert len(cached_load) == 2
    assert cached_load[0].text == "updated"
    assert cached_load[1].text == "new"


def test_cache_can_be_disabled(tmp_path) -> None:
    """Test that caching can be disabled via use_cache parameter."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), use_cache=False)

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # First load
    storage.load()

    # With cache disabled, even a second load should re-read the file
    original_read_text = Path.read_text
    read_count = [0]

    def tracking_read_text(self, *args, **kwargs):
        read_count[0] += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", tracking_read_text):
        second_load = storage.load()

    # Should have re-read the file (not using cache)
    assert read_count[0] == 1, "With cache disabled, should re-read file"

    # Data should still be correct
    assert second_load[0].text == "initial"


def test_load_returns_empty_list_for_nonexistent_file(tmp_path) -> None:
    """Test that load() returns empty list when file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []

    # Second call should also return empty (cached)
    result2 = storage.load()
    assert result2 == []


def test_cache_handles_file_created_after_initial_load(tmp_path) -> None:
    """Test that cache correctly handles file created after initial load."""
    db = tmp_path / "new.json"
    storage = TodoStorage(str(db))

    # First load - file doesn't exist, should return empty and cache that
    first_load = storage.load()
    assert first_load == []

    # Now create the file externally
    time.sleep(0.01)  # Ensure mtime is different
    new_data = [{"id": 1, "text": "newly created", "done": False}]
    db.write_text(json.dumps(new_data), encoding="utf-8")

    # Second load - should detect new file and load it
    second_load = storage.load()
    assert len(second_load) == 1
    assert second_load[0].text == "newly created"

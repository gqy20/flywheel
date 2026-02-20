"""Tests for issue #4749: load() caching mechanism.

This test suite verifies that TodoStorage.load() implements caching
to avoid redundant file reads when the file hasn't changed.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_caches_result_when_file_unchanged(tmp_path) -> None:
    """Test that repeated load() calls use cache when file hasn't changed."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="cached")]
    storage.save(todos)

    # First load - should read from file
    first_load = storage.load()
    assert len(first_load) == 1
    assert first_load[0].text == "cached"

    # Second load - should use cache (no additional file read)
    with patch.object(Path, "read_text", wraps=db.read_text) as mock_read:
        second_load = storage.load()
        assert len(second_load) == 1
        assert second_load[0].text == "cached"
        # Should NOT have read the file again since file mtime unchanged
        mock_read.assert_not_called()


def test_cache_invalidated_on_file_change(tmp_path) -> None:
    """Test that cache is invalidated when file is modified externally."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="original")]
    storage.save(todos)

    # First load
    first_load = storage.load()
    assert first_load[0].text == "original"

    # Modify file externally (not via storage.save)
    import time

    time.sleep(0.01)  # Ensure mtime changes
    new_data = [{"id": 1, "text": "modified externally", "done": False}]
    db.write_text(json.dumps(new_data), encoding="utf-8")

    # Second load - should detect file change and reload
    second_load = storage.load()
    assert second_load[0].text == "modified externally"


def test_cache_refreshed_after_save(tmp_path) -> None:
    """Test that save() refreshes the cache for subsequent loads."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save initial data
    todos = [Todo(id=1, text="first")]
    storage.save(todos)

    # Load once to populate cache
    first_load = storage.load()
    assert first_load[0].text == "first"

    # Save new data - should update cache
    new_todos = [Todo(id=1, text="second"), Todo(id=2, text="new")]
    storage.save(new_todos)

    # Load again - should return cached value (same as what was saved)
    with patch.object(Path, "read_text", wraps=db.read_text) as mock_read:
        cached_load = storage.load()
        assert len(cached_load) == 2
        assert cached_load[0].text == "second"
        # Should use cache since save() updated it
        mock_read.assert_not_called()


def test_load_performance_with_caching(tmp_path) -> None:
    """Benchmark: multiple loads should be faster with caching."""
    import time

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create some data
    todos = [Todo(id=i, text=f"task {i}") for i in range(100)]
    storage.save(todos)

    # Measure time for multiple loads
    start = time.perf_counter()
    for _ in range(100):
        storage.load()
    elapsed = time.perf_counter() - start

    # With caching, this should be very fast (under 10ms for 100 loads)
    # Without caching, it would involve 100 file reads
    assert elapsed < 0.1, f"100 loads took {elapsed:.3f}s - caching may not be working"


def test_different_storage_instances_have_separate_caches(tmp_path) -> None:
    """Test that each storage instance maintains its own cache."""
    db = tmp_path / "todo.json"

    storage1 = TodoStorage(str(db))
    storage2 = TodoStorage(str(db))

    # Save via storage1
    todos = [Todo(id=1, text="shared")]
    storage1.save(todos)

    # Both should load the same data
    load1 = storage1.load()
    load2 = storage2.load()

    assert load1[0].text == "shared"
    assert load2[0].text == "shared"

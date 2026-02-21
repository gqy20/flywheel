"""Tests for issue #4989: In-memory caching with optional invalidation for load().

This test suite verifies that TodoStorage supports optional caching with:
- cache_enabled parameter (default False for backward compatibility)
- Cache returns same data on repeated load() without disk read
- Cache invalidates after save() operation
- Cache invalidates when file mtime changes externally
- invalidate_cache() method for manual cache clearing
"""

from __future__ import annotations

import time
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestCacheDisabledByDefault:
    """Tests for default behavior when caching is disabled."""

    def test_cache_disabled_always_reads_from_disk(self, tmp_path: Path) -> None:
        """When cache_enabled=False (default), load() always reads from disk."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Initial save
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Load once
        loaded1 = storage.load()
        assert len(loaded1) == 1
        assert loaded1[0].text == "initial"

        # Modify file externally
        db.write_text('[{"id": 1, "text": "modified", "done": false}]', encoding="utf-8")

        # Load again - should see the change (no caching)
        loaded2 = storage.load()
        assert len(loaded2) == 1
        assert loaded2[0].text == "modified"


class TestCacheEnabled:
    """Tests for caching behavior when cache_enabled=True."""

    def test_cache_enabled_returns_cached_data_on_repeated_load(self, tmp_path: Path) -> None:
        """When cache_enabled=True, second load() returns cached data without disk read."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Initial save
        todos = [Todo(id=1, text="cached")]
        storage.save(todos)

        # Load once - should read from disk and cache
        loaded1 = storage.load()
        assert len(loaded1) == 1
        assert loaded1[0].text == "cached"

        # Load again without any external changes - should return cached data
        loaded2 = storage.load()
        assert loaded2 is loaded1  # Same object reference = cached

        # Third load also returns same cached data
        loaded3 = storage.load()
        assert loaded3 is loaded1  # Still same object

    def test_cache_invalidates_after_save(self, tmp_path: Path) -> None:
        """Cache is automatically invalidated after save() operation."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Initial save
        todos = [Todo(id=1, text="original")]
        storage.save(todos)

        # Load and cache
        loaded1 = storage.load()
        assert loaded1[0].text == "original"

        # Save new data - should invalidate cache
        new_todos = [Todo(id=1, text="updated")]
        storage.save(new_todos)

        # Modify file externally after save
        db.write_text('[{"id": 1, "text": "external", "done": false}]', encoding="utf-8")

        # Load again - should see external change (cache was invalidated by save)
        loaded2 = storage.load()
        assert loaded2[0].text == "external"

    def test_cache_invalidates_on_external_mtime_change(self, tmp_path: Path) -> None:
        """Cache detects external file changes via mtime comparison and invalidates."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Initial save
        todos = [Todo(id=1, text="original")]
        storage.save(todos)

        # Load and cache
        loaded1 = storage.load()
        assert loaded1[0].text == "original"

        # Modify file externally with a time gap to ensure mtime changes
        time.sleep(0.01)  # Small sleep to ensure mtime difference
        db.write_text('[{"id": 1, "text": "external-change", "done": false}]', encoding="utf-8")

        # Load again - should detect mtime change and reload from disk
        loaded2 = storage.load()
        assert loaded2[0].text == "external-change"


class TestManualCacheInvalidation:
    """Tests for manual cache invalidation."""

    def test_invalidate_cache_method_clears_cache(self, tmp_path: Path) -> None:
        """invalidate_cache() method allows manual cache clearing."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Initial save
        todos = [Todo(id=1, text="original")]
        storage.save(todos)

        # Load and cache
        loaded1 = storage.load()
        assert loaded1[0].text == "original"

        # Modify file externally
        db.write_text('[{"id": 1, "text": "external", "done": false}]', encoding="utf-8")

        # Manually invalidate cache
        storage.invalidate_cache()

        # Load again - should read fresh data from disk
        loaded2 = storage.load()
        assert loaded2[0].text == "external"


class TestCacheEdgeCases:
    """Tests for edge cases in caching behavior."""

    def test_cache_with_nonexistent_file(self, tmp_path: Path) -> None:
        """Cache handles nonexistent file correctly."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Load from nonexistent file - should return empty list
        loaded1 = storage.load()
        assert loaded1 == []

        # Create file externally
        db.write_text('[{"id": 1, "text": "created", "done": false}]', encoding="utf-8")

        # Load again - should detect new file (mtime changed from nonexistent)
        loaded2 = storage.load()
        assert len(loaded2) == 1
        assert loaded2[0].text == "created"

    def test_cache_disabled_mode_ignores_invalidate_cache(self, tmp_path: Path) -> None:
        """invalidate_cache() is a no-op when caching is disabled."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=False)

        # Should not raise
        storage.invalidate_cache()

        # Save and load should work normally
        todos = [Todo(id=1, text="test")]
        storage.save(todos)
        loaded = storage.load()
        assert loaded[0].text == "test"

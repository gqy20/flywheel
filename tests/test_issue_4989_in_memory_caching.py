"""Tests for in-memory caching with optional invalidation for load().

Issue: #4989
Feature: Add optional cache_enabled parameter to TodoStorage with:
- Cache disabled (default) always reads from disk
- Cache enabled returns cached data on repeated load() without disk read
- Cache invalidates after save()
- Cache detects external file changes via mtime comparison
- Manual cache invalidation via invalidate_cache() method
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestCacheDisabledDefault:
    """Tests that verify cache disabled (default) behavior matches current implementation."""

    def test_cache_disabled_by_default(self, tmp_path: Path) -> None:
        """Cache should be disabled by default for backward compatibility."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))
        assert not storage.cache_enabled

    def test_cache_disabled_always_reads_from_disk(self, tmp_path: Path) -> None:
        """When cache disabled, each load() should read from disk."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=False)

        # Save initial data
        storage.save([Todo(id=1, text="initial")])

        # First load
        todos1 = storage.load()
        assert len(todos1) == 1
        assert todos1[0].text == "initial"

        # Modify file externally (simulate another process)
        db.write_text('[{"id": 1, "text": "modified", "done": false}]')

        # Second load should see the external change (no cache)
        todos2 = storage.load()
        assert len(todos2) == 1
        assert todos2[0].text == "modified"


class TestCacheEnabled:
    """Tests for cache_enabled=True behavior."""

    def test_cache_enabled_returns_same_data_on_repeated_load(
        self, tmp_path: Path
    ) -> None:
        """When cache enabled, second load() returns cached data without disk read."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)
        assert storage.cache_enabled

        # Save initial data
        storage.save([Todo(id=1, text="cached data")])

        # First load - populates cache
        todos1 = storage.load()
        assert len(todos1) == 1
        assert todos1[0].text == "cached data"

        # Track disk reads - patch the file read to verify caching
        with patch.object(
            Path, "read_text", wraps=db.read_text
        ) as mock_read:
            # Second load should use cache, NOT read from disk
            todos2 = storage.load()
            assert len(todos2) == 1
            assert todos2[0].text == "cached data"
            # File should NOT have been read
            mock_read.assert_not_called()

    def test_cache_enabled_external_file_change_detected(
        self, tmp_path: Path
    ) -> None:
        """Cache should invalidate when file mtime changes externally."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Save initial data
        storage.save([Todo(id=1, text="initial")])

        # First load - populates cache
        todos1 = storage.load()
        assert todos1[0].text == "initial"

        # Wait a moment and modify file externally (changes mtime)
        time.sleep(0.01)
        db.write_text('[{"id": 1, "text": "external change", "done": false}]')

        # Second load should detect mtime change and re-read from disk
        todos2 = storage.load()
        assert todos2[0].text == "external change"


class TestCacheInvalidation:
    """Tests for cache invalidation behavior."""

    def test_cache_invalidates_after_save(self, tmp_path: Path) -> None:
        """Cache should be automatically invalidated after save() operation."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Save initial data
        storage.save([Todo(id=1, text="initial")])

        # First load - populates cache
        todos1 = storage.load()
        assert todos1[0].text == "initial"

        # Save new data - should invalidate cache
        storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])

        # Load after save should get fresh data
        todos2 = storage.load()
        assert len(todos2) == 2
        assert todos2[0].text == "updated"
        assert todos2[1].text == "new"

    def test_invalidate_cache_method_clears_cache(self, tmp_path: Path) -> None:
        """Manual invalidate_cache() method should clear the cache."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Save initial data
        storage.save([Todo(id=1, text="initial")])

        # First load - populates cache
        todos1 = storage.load()
        assert todos1[0].text == "initial"

        # Manually invalidate cache
        storage.invalidate_cache()

        # Modify file externally
        db.write_text('[{"id": 1, "text": "modified", "done": false}]')

        # Load after invalidate should read from disk (not cache)
        todos2 = storage.load()
        assert todos2[0].text == "modified"

    def test_invalidate_cache_safe_when_file_not_exists(self, tmp_path: Path) -> None:
        """invalidate_cache() should be safe to call when file doesn't exist."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Should not raise
        storage.invalidate_cache()

        # Can still load empty list
        todos = storage.load()
        assert todos == []


class TestCacheWithNonexistentFile:
    """Tests for cache behavior when file doesn't exist."""

    def test_cache_enabled_load_empty_when_file_missing(
        self, tmp_path: Path
    ) -> None:
        """When file doesn't exist, load() should return empty list and cache it."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Load from non-existent file
        todos1 = storage.load()
        assert todos1 == []

        # Verify cache is populated (even for empty result)
        assert storage._cache == []
        assert storage._cache_mtime is None

        # Second load should return cached empty list without disk read
        # We verify by checking that _is_cache_valid returns True
        assert storage._is_cache_valid()

        todos2 = storage.load()
        assert todos2 == []


class TestCacheMtimeTracking:
    """Tests for mtime-based cache invalidation."""

    def test_cache_tracks_mtime_on_load(self, tmp_path: Path) -> None:
        """Cache should track file mtime when loading data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        storage.save([Todo(id=1, text="test")])

        # Load and verify mtime is tracked
        storage.load()
        assert storage._cache_mtime is not None

    def test_cache_invalidate_on_mtime_change(self, tmp_path: Path) -> None:
        """Cache should invalidate when mtime differs from cached value."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        storage.save([Todo(id=1, text="original")])

        # First load caches data with mtime
        todos1 = storage.load()
        assert todos1[0].text == "original"

        # Wait and modify file externally (changes mtime)
        time.sleep(0.01)
        db.write_text('[{"id": 1, "text": "changed", "done": false}]')

        # Second load should detect change via mtime comparison
        todos2 = storage.load()
        assert todos2[0].text == "changed"

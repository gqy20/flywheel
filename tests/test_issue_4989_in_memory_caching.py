"""Tests for in-memory caching with optional invalidation for load().

Issue #4989: Add in-memory caching with optional invalidation for load()

This test suite verifies:
- TodoStorage accepts cache_enabled parameter (default False for backward compatibility)
- When cache_enabled=True, second load() returns cached data without disk read
- Cache is automatically invalidated after save() operation
- Cache detects external file changes via mtime comparison and invalidates stale cache
- New invalidate_cache() method allows manual cache clearing
- Default behavior (cache_enabled=False) performs identically to current implementation
"""

from __future__ import annotations

import time
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestCacheDisabledDefault:
    """Tests for default behavior with cache disabled."""

    def test_cache_disabled_always_reads_from_disk(self, tmp_path: Path) -> None:
        """Test cache disabled (default) always reads from disk."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial todos
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Load twice - should read from disk both times
        loaded1 = storage.load()
        loaded2 = storage.load()

        assert len(loaded1) == 1
        assert loaded1[0].text == "initial"
        assert len(loaded2) == 1
        assert loaded2[0].text == "initial"

    def test_cache_disabled_detects_external_changes(self, tmp_path: Path) -> None:
        """Test that without caching, external file changes are detected."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial todos
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Load once
        loaded1 = storage.load()
        assert loaded1[0].text == "initial"

        # Modify file externally
        import json

        db.write_text(json.dumps([{"id": 1, "text": "modified externally", "done": False}]))

        # Load again - should see the external change
        loaded2 = storage.load()
        assert loaded2[0].text == "modified externally"


class TestCacheEnabled:
    """Tests for cache enabled behavior."""

    def test_cache_enabled_returns_cached_data(self, tmp_path: Path) -> None:
        """Test cache enabled returns same data on repeated load() without disk read."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Create initial todos
        todos = [Todo(id=1, text="initial"), Todo(id=2, text="second")]
        storage.save(todos)

        # Load twice - should return cached data
        loaded1 = storage.load()
        loaded2 = storage.load()
        loaded3 = storage.load()

        assert len(loaded1) == 2
        assert loaded1[0].text == "initial"
        # All loads should return the same cached data
        assert len(loaded2) == 2
        assert len(loaded3) == 2

    def test_cache_enabled_uses_memory_cache(self, tmp_path: Path) -> None:
        """Test that cached data is returned from memory, not disk."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Create initial todos
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Load once to populate cache
        storage.load()

        # Modify file externally (this should NOT be reflected due to cache)
        import json

        db.write_text(json.dumps([{"id": 1, "text": "modified externally", "done": False}]))

        # Load again - should return cached data, not modified file
        loaded2 = storage.load()
        assert loaded2[0].text == "initial"


class TestCacheInvalidation:
    """Tests for cache invalidation behavior."""

    def test_cache_invalidates_after_save(self, tmp_path: Path) -> None:
        """Test cache invalidates after save()."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Create initial todos
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Load to populate cache
        loaded1 = storage.load()
        assert loaded1[0].text == "initial"

        # Save new todos - should invalidate cache
        new_todos = [Todo(id=1, text="modified"), Todo(id=2, text="added")]
        storage.save(new_todos)

        # Load again - should see the new data
        loaded2 = storage.load()
        assert len(loaded2) == 2
        assert loaded2[0].text == "modified"

    def test_cache_invalidates_on_file_mtime_change(self, tmp_path: Path) -> None:
        """Test cache invalidates when file mtime changes externally."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Create initial todos
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Load to populate cache
        loaded1 = storage.load()
        assert loaded1[0].text == "initial"

        # Small delay to ensure mtime changes
        time.sleep(0.01)

        # Modify file externally (change mtime and content)
        import json

        db.write_text(json.dumps([{"id": 1, "text": "external modification", "done": False}]))

        # Load again - should detect mtime change and reload from disk
        loaded2 = storage.load()
        assert loaded2[0].text == "external modification"

    def test_invalidate_cache_method(self, tmp_path: Path) -> None:
        """Test new invalidate_cache() method allows manual cache clearing."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Create initial todos
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Load to populate cache
        loaded1 = storage.load()
        assert loaded1[0].text == "initial"

        # Modify file externally
        import json

        db.write_text(json.dumps([{"id": 1, "text": "external modification", "done": False}]))

        # Manually invalidate cache
        storage.invalidate_cache()

        # Load again - should reload from disk
        loaded2 = storage.load()
        assert loaded2[0].text == "external modification"


class TestCacheParameterValidation:
    """Tests for cache_enabled parameter validation."""

    def test_cache_enabled_parameter_accepted(self, tmp_path: Path) -> None:
        """Test TodoStorage accepts cache_enabled parameter."""
        db = tmp_path / "todo.json"

        # Should accept cache_enabled=True
        storage = TodoStorage(str(db), cache_enabled=True)
        assert storage is not None

        # Should accept cache_enabled=False
        storage2 = TodoStorage(str(db), cache_enabled=False)
        assert storage2 is not None

    def test_cache_enabled_default_is_false(self, tmp_path: Path) -> None:
        """Test cache_enabled defaults to False for backward compatibility."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Default should be False (no caching)
        # Verify by modifying file externally and checking load sees the change
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        storage.load()

        import json

        db.write_text(json.dumps([{"id": 1, "text": "modified", "done": False}]))

        loaded = storage.load()
        assert loaded[0].text == "modified"


class TestCacheEdgeCases:
    """Edge case tests for caching."""

    def test_cache_handles_empty_file(self, tmp_path: Path) -> None:
        """Test cache handles empty file correctly."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Load from non-existent file
        loaded1 = storage.load()
        assert loaded1 == []

        # Load again - should return cached empty list
        loaded2 = storage.load()
        assert loaded2 == []

    def test_cache_after_invalidation_behaves_correctly(self, tmp_path: Path) -> None:
        """Test that after invalidation, caching still works for unchanged files."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), cache_enabled=True)

        # Create initial todos
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Load to populate cache
        storage.load()

        # Invalidate
        storage.invalidate_cache()

        # Load again - populates cache anew
        loaded1 = storage.load()
        assert loaded1[0].text == "initial"

        # Load again without modifying file - should use cache
        # (mtime unchanged, so cache is valid)
        loaded2 = storage.load()
        assert loaded2[0].text == "initial"

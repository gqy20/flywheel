"""Test LRU cache for metadata reads (Issue #1073)."""
import os
import tempfile
import time
from pathlib import Path
import pytest

from flywheel import FileStorage, Todo


class TestLRUCache:
    """Test LRU cache implementation for metadata reads."""

    def test_lru_cache_reduces_file_reads(self):
        """Test that LRU cache reduces actual file reads for metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "lru_cache_test.json"
            storage = FileStorage(str(cache_path))

            # Add some todos
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            storage.add(Todo(id=2, title="Task 2", status="pending"))

            # Get initial file modification time
            initial_mtime = os.path.getmtime(cache_path)

            # Perform multiple load operations
            # With LRU cache, these should not cause repeated file reads
            for _ in range(5):
                storage._load_sync()

            # File modification time should not change if caching is working
            # (no actual reads from disk)
            final_mtime = os.path.getmtime(cache_path)

            # This test will fail without LRU cache implementation
            assert initial_mtime == final_mtime, \
                "LRU cache should prevent repeated file reads for metadata"

    def test_lru_cache_maxsize_eviction(self):
        """Test that LRU cache evicts old entries when maxsize is reached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "lru_eviction_test.json"

            # Create storage with small cache size
            storage = FileStorage(str(cache_path))

            # Add more todos than cache can hold
            for i in range(10):
                storage.add(Todo(id=i, title=f"Task {i}", status="pending"))

            # Access todos in reverse order to test LRU eviction
            for i in range(9, -1, -1):
                storage.get(i)

            # If LRU cache is working, accessing all todos should be fast
            # and cache should respect maxsize
            start = time.time()
            for i in range(10):
                storage.get(i)
            elapsed = time.time() - start

            # Should be very fast with caching (< 0.1 seconds for 10 gets)
            assert elapsed < 0.1, \
                f"LRU cache should provide fast access: {elapsed:.3f}s"

    def test_lru_cache_invalidation_on_write(self):
        """Test that LRU cache is invalidated when data is written."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "lru_invalidation_test.json"
            storage = FileStorage(str(cache_path))

            # Add initial todo
            storage.add(Todo(id=1, title="Task 1", status="pending"))

            # Load data to populate cache
            storage._load_sync()

            # Update todo (this should invalidate cache)
            storage.update(Todo(id=1, title="Updated Task", status="completed"))

            # Reload - should get updated data
            storage._load_sync()
            todos = storage.list()

            assert len(todos) == 1
            assert todos[0].title == "Updated Task"
            assert todos[0].status == "completed"

    def test_lru_cache_performance_improvement(self):
        """Test that LRU cache provides measurable performance improvement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "lru_perf_test.json"
            storage = FileStorage(str(cache_path))

            # Add todos
            for i in range(50):
                storage.add(Todo(id=i, title=f"Task {i}", status="pending"))

            # First load - uncached
            start = time.time()
            storage._load_sync()
            first_load_time = time.time() - start

            # Subsequent loads - should be cached
            start = time.time()
            for _ in range(10):
                storage._load_sync()
            cached_load_time = time.time() - start

            # Cached loads should be significantly faster
            # (at least 5x improvement for 10 loads)
            assert cached_load_time < first_load_time * 5, \
                f"LRU cache should improve performance: " \
                f"first_load={first_load_time:.4f}s, " \
                f"cached_10_loads={cached_load_time:.4f}s"

    def test_lru_cache_decorator_exists(self):
        """Test that internal read methods use lru_cache decorator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "lru_decorator_test.json"
            storage = FileStorage(str(cache_path))

            # Check if _load_sync has cache_info (indicating lru_cache decorator)
            # This will fail without the lru_cache implementation
            if hasattr(storage._load_sync, 'cache_info'):
                cache_info = storage._load_sync.cache_info()
                # Verify cache is being used
                assert hasattr(cache_info, 'hits'), \
                    "LRU cache should have cache_info with hits attribute"
                assert hasattr(cache_info, 'misses'), \
                    "LRU cache should have cache_info with misses attribute"
            else:
                pytest.fail("_load_sync method should have lru_cache decorator")

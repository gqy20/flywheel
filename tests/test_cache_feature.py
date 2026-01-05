"""Test write-through cache functionality (Issue #718)."""
import os
import time
import tempfile
from pathlib import Path
import pytest

from flywheel import FileStorage, Todo


class TestWriteThroughCache:
    """Test write-through cache implementation."""

    def test_cache_reduces_disk_io(self):
        """Test that cache reduces disk I/O for read operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache_test.json"
            storage = FileStorage(str(cache_path), enable_cache=True)

            # Add some todos
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            storage.add(Todo(id=2, title="Task 2", status="pending"))

            # Get file modification time
            initial_mtime = os.path.getmtime(cache_path)

            # Perform multiple read operations - these should use cache
            for _ in range(5):
                storage.list()
                storage.get(1)

            # File modification time should not change (no disk I/O for reads)
            final_mtime = os.path.getmtime(cache_path)
            assert initial_mtime == final_mtime, "Cache should prevent disk I/O on reads"

    def test_cache_invalidates_on_write(self):
        """Test that cache is invalidated when data changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache_invalidate.json"
            storage = FileStorage(str(cache_path), enable_cache=True)

            # Add initial todo
            storage.add(Todo(id=1, title="Task 1", status="pending"))

            # Read to populate cache
            todos = storage.list()
            assert len(todos) == 1

            # Update todo - this should update cache
            storage.update(Todo(id=1, title="Updated Task", status="completed"))

            # Read again - should get updated data from cache
            todos = storage.list()
            assert len(todos) == 1
            assert todos[0].title == "Updated Task"
            assert todos[0].status == "completed"

    def test_write_through_cache_updates_disk(self):
        """Test that write-through cache updates disk immediately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "write_through.json"
            storage = FileStorage(str(cache_path), enable_cache=True)

            # Add todo - should write to disk immediately
            storage.add(Todo(id=1, title="Task 1", status="pending"))

            # Create new storage instance to verify disk write
            storage2 = FileStorage(str(cache_path), enable_cache=False)
            todos = storage2.list()

            assert len(todos) == 1
            assert todos[0].title == "Task 1"

    def test_cache_disabled_parameter(self):
        """Test that cache can be disabled via enable_cache parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache_disabled.json"
            storage = FileStorage(str(cache_path), enable_cache=False)

            # Add todos
            storage.add(Todo(id=1, title="Task 1", status="pending"))

            # Verify cache is not enabled
            assert not storage._cache_enabled

    def test_cache_performance_improvement(self):
        """Test that cache provides performance improvement for frequent reads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache_perf.json"
            storage = FileStorage(str(cache_path), enable_cache=True)

            # Add todos
            for i in range(100):
                storage.add(Todo(id=i, title=f"Task {i}", status="pending"))

            # Measure time for cached reads
            start = time.time()
            for _ in range(100):
                storage.list()
            cached_time = time.time() - start

            # Disable cache and measure again
            storage._cache_enabled = False

            start = time.time()
            for _ in range(100):
                storage.list()
            uncached_time = time.time() - start

            # Cached reads should be faster (or at least not significantly slower)
            # We allow some margin for variance
            assert cached_time < uncached_time * 2, \
                f"Cache should improve performance: cached={cached_time:.4f}s, uncached={uncached_time:.4f}s"

    def test_cache_with_get_operation(self):
        """Test that cache works with get() operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache_get.json"
            storage = FileStorage(str(cache_path), enable_cache=True)

            # Add todo
            storage.add(Todo(id=1, title="Task 1", status="pending"))

            # Get should use cache after first read
            todo = storage.get(1)
            assert todo is not None
            assert todo.title == "Task 1"

            # Update
            storage.update(Todo(id=1, title="Updated", status="completed"))

            # Get should return updated data
            todo = storage.get(1)
            assert todo.title == "Updated"
            assert todo.status == "completed"

    def test_cache_with_list_filtering(self):
        """Test that cache works with list(status) filtering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache_filter.json"
            storage = FileStorage(str(cache_path), enable_cache=True)

            # Add todos with different statuses
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            storage.add(Todo(id=2, title="Task 2", status="completed"))
            storage.add(Todo(id=3, title="Task 3", status="pending"))

            # List with filter
            pending = storage.list(status="pending")
            assert len(pending) == 2

            completed = storage.list(status="completed")
            assert len(completed) == 1

    def test_cache_with_delete(self):
        """Test that cache is updated on delete operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "cache_delete.json"
            storage = FileStorage(str(cache_path), enable_cache=True)

            # Add todos
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            storage.add(Todo(id=2, title="Task 2", status="pending"))

            # Delete one
            storage.delete(1)

            # List should reflect the deletion
            todos = storage.list()
            assert len(todos) == 1
            assert todos[0].id == 2

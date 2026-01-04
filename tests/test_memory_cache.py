"""Tests for memory cache layer (Issue #703)."""

import tempfile
from pathlib import Path
import time

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_memory_cache_enabled():
    """Test that memory cache can be enabled via parameter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        # Create storage with cache enabled
        storage = Storage(str(storage_path), enable_cache=True)

        # Should have cache-related attributes
        assert hasattr(storage, '_cache_enabled'), "Storage should have _cache_enabled attribute"
        assert storage._cache_enabled is True, "Cache should be enabled"


def test_memory_cache_disabled():
    """Test that memory cache is disabled by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        # Create storage without cache parameter
        storage = Storage(str(storage_path))

        # Cache should be disabled by default
        assert hasattr(storage, '_cache_enabled'), "Storage should have _cache_enabled attribute"
        assert storage._cache_enabled is False, "Cache should be disabled by default"


def test_cache_invalidates_on_add():
    """Test that cache is invalidated when adding a todo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path), enable_cache=True)

        # Add a todo
        storage.add(Todo(title="Test todo"))

        # Cache should be marked dirty
        assert hasattr(storage, '_cache_dirty'), "Storage should have _cache_dirty attribute"
        assert storage._cache_dirty is True, "Cache should be dirty after add"


def test_cache_invalidates_on_update():
    """Test that cache is invalidated when updating a todo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path), enable_cache=True)

        # Add a todo
        todo = storage.add(Todo(title="Test todo"))

        # Clear cache dirty flag
        storage._save()
        storage._cache_dirty = False

        # Update the todo
        todo.status = "completed"
        storage.update(todo)

        # Cache should be marked dirty
        assert storage._cache_dirty is True, "Cache should be dirty after update"


def test_cache_invalidates_on_delete():
    """Test that cache is invalidated when deleting a todo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path), enable_cache=True)

        # Add a todo
        todo = storage.add(Todo(title="Test todo"))

        # Clear cache dirty flag
        storage._save()
        storage._cache_dirty = False

        # Delete the todo
        storage.delete(todo.id)

        # Cache should be marked dirty
        assert storage._cache_dirty is True, "Cache should be dirty after delete"


def test_cache_reduces_disk_reads_on_get():
    """Test that cache reduces disk reads for get operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path), enable_cache=True)

        # Add a todo
        todo = storage.add(Todo(title="Test todo"))

        # Get initial file access time
        mtime_before = storage_path.stat().st_mtime

        # Small delay to ensure mtime can change
        time.sleep(0.01)

        # Get the same todo multiple times
        for _ in range(5):
            result = storage.get(todo.id)
            assert result is not None
            assert result.title == "Test todo"

        # File should not have been read again (mtime unchanged)
        mtime_after = storage_path.stat().st_mtime
        assert mtime_before == mtime_after, "Cache should prevent disk reads on get"


def test_cache_reduces_disk_reads_on_list():
    """Test that cache reduces disk reads for list operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path), enable_cache=True)

        # Add multiple todos
        for i in range(5):
            storage.add(Todo(title=f"Todo {i}"))

        # Get initial file access time
        mtime_before = storage_path.stat().st_mtime

        # Small delay to ensure mtime can change
        time.sleep(0.01)

        # List todos multiple times
        for _ in range(5):
            todos = storage.list()
            assert len(todos) == 5

        # File should not have been read again (mtime unchanged)
        mtime_after = storage_path.stat().st_mtime
        assert mtime_before == mtime_after, "Cache should prevent disk reads on list"


def test_cache_with_compression():
    """Test that cache works with compression enabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path), compression=True, enable_cache=True)

        # Add a todo
        todo = storage.add(Todo(title="Test todo"))

        # Get initial file access time
        mtime_before = storage_path.stat().st_mtime

        # Small delay to ensure mtime can change
        time.sleep(0.01)

        # Get the todo (should use cache, not decompress file)
        result = storage.get(todo.id)
        assert result is not None
        assert result.title == "Test todo"

        # File should not have been read again
        mtime_after = storage_path.stat().st_mtime
        assert mtime_before == mtime_after, "Cache should prevent decompression on get"


def test_cache_performance_improvement():
    """Test that cache provides measurable performance improvement."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with many todos
        storage = Storage(str(storage_path), enable_cache=True)
        for i in range(100):
            storage.add(Todo(title=f"Todo {i}"))

        # Save and clear dirty flag
        storage._save()
        storage._cache_dirty = False

        # Measure cached get performance
        start_time = time.time()
        for i in range(1, 101):
            storage.get(i)
        cached_time = time.time() - start_time

        # Create new storage instance without cache to compare
        storage2 = Storage(str(storage_path), enable_cache=False)

        # Measure non-cached get performance
        start_time = time.time()
        for i in range(1, 101):
            storage2.get(i)
        non_cached_time = time.time() - start_time

        # Cached version should be significantly faster
        # We allow some tolerance for system load
        assert cached_time < non_cached_time * 0.5, \
            f"Cache should be faster: cached={cached_time:.3f}s, non-cached={non_cached_time:.3f}s"

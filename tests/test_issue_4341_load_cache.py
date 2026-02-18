"""Tests for issue #4341: load method should cache 'file not exist' result.

Issue: The load method in TodoStorage doesn't cache results when a file
doesn't exist, causing repeated file existence checks during high-frequency
read scenarios.

This test verifies that when a file doesn't exist, subsequent load() calls
don't repeatedly check file existence (by mocking Path.exists).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage


def test_load_caches_file_not_exist_result(tmp_path: Path) -> None:
    """Test that load() caches 'file not exist' result to avoid repeated checks.

    When the file doesn't exist:
    1. First load() call should check Path.exists()
    2. Subsequent load() calls should NOT re-check Path.exists()
       because the result is cached.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File should not exist
    assert not db.exists()

    # Track how many times Path.exists() is called
    exists_call_count = 0
    original_exists = Path.exists

    def tracking_exists(self) -> bool:
        nonlocal exists_call_count
        exists_call_count += 1
        return original_exists(self)

    # Patch Path.exists to track calls
    with patch.object(Path, "exists", tracking_exists):
        # First load - should check exists
        result1 = storage.load()
        assert result1 == []
        assert exists_call_count == 1, "First load should check exists() once"

        # Second load - should NOT re-check exists due to caching
        result2 = storage.load()
        assert result2 == []
        # With caching, exists should not be called again
        assert exists_call_count == 1, (
            "Second load should use cached result, not re-check exists()"
        )

        # Third load - still should NOT re-check
        result3 = storage.load()
        assert result3 == []
        assert exists_call_count == 1, (
            "Third load should use cached result, not re-check exists()"
        )


def test_load_cache_invalidated_after_save(tmp_path: Path) -> None:
    """Test that cache is invalidated after save() creates the file.

    When a file is created via save(), the cache should be invalidated
    so that subsequent load() calls read from the actual file.
    """
    from flywheel.todo import Todo

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First load with no file - should return empty list
    result1 = storage.load()
    assert result1 == []

    # Now save creates the file
    storage.save([Todo(id=1, text="test")])

    # Load should now read from file, not use cached empty list
    result2 = storage.load()
    assert len(result2) == 1
    assert result2[0].text == "test"


def test_load_cache_with_multiple_storage_instances(tmp_path: Path) -> None:
    """Test that caching is per-instance.

    Each TodoStorage instance should have its own cache.
    """
    db1 = tmp_path / "db1.json"
    db2 = tmp_path / "db2.json"

    storage1 = TodoStorage(str(db1))
    storage2 = TodoStorage(str(db2))

    # Both don't exist, both return empty
    assert storage1.load() == []
    assert storage2.load() == []

    # Create file for storage1
    from flywheel.todo import Todo
    storage1.save([Todo(id=1, text="in db1")])

    # storage1 should see the file, storage2 still returns empty
    assert len(storage1.load()) == 1
    assert storage2.load() == []

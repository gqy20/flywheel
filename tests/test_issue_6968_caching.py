"""Tests for TodoApp caching behavior (issue #6968).

This test suite verifies that TodoApp implements in-memory caching
to avoid loading/saving the entire file on each operation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.cli import TodoApp
from flywheel.todo import Todo
from flywheel.storage import TodoStorage


class TestTodoAppCaching:
    """Test that TodoApp caches todos in memory."""

    def test_add_operation_caches_todos(self, tmp_path: Path) -> None:
        """Test that after add, todos are cached in memory."""
        db = tmp_path / "todo.json"
        app = TodoApp(db_path=str(db))

        # Add a todo
        todo1 = app.add("First task")

        # The cache should now contain the todo
        assert hasattr(app, "_cache"), "TodoApp should have a _cache attribute"
        assert len(app._cache) == 1
        assert app._cache[0].text == "First task"

        # Add another todo
        todo2 = app.add("Second task")

        # Cache should now have 2 items
        assert len(app._cache) == 2

    def test_list_operation_uses_cache(self, tmp_path: Path) -> None:
        """Test that list() uses cache instead of reloading from file."""
        db = tmp_path / "todo.json"
        app = TodoApp(db_path=str(db))

        # Add todos
        app.add("Task 1")
        app.add("Task 2")

        # Patch storage.load to track if it's called
        with patch.object(app.storage, "load", wraps=app.storage.load) as mock_load:
            # list() should use cache, not reload from file
            todos = app.list()

            # If caching works, load should not be called again
            # (it was already called during add operations)
            assert len(todos) == 2
            # load should not have been called during list()
            assert mock_load.call_count == 0, "list() should use cache, not call storage.load()"

    def test_mark_done_uses_cache(self, tmp_path: Path) -> None:
        """Test that mark_done() uses cache and doesn't reload."""
        db = tmp_path / "todo.json"
        app = TodoApp(db_path=str(db))

        # Add a todo
        app.add("Task to complete")

        # Patch storage.load to track if it's called
        with patch.object(app.storage, "load", wraps=app.storage.load) as mock_load:
            app.mark_done(1)

            # load should not be called (using cache)
            assert mock_load.call_count == 0, "mark_done() should use cache"

        # Verify the todo is marked done in cache
        assert app._cache[0].done is True

    def test_remove_uses_cache(self, tmp_path: Path) -> None:
        """Test that remove() uses cache and doesn't reload."""
        db = tmp_path / "todo.json"
        app = TodoApp(db_path=str(db))

        # Add todos
        app.add("Task 1")
        app.add("Task 2")

        # Patch storage.load to track if it's called
        with patch.object(app.storage, "load", wraps=app.storage.load) as mock_load:
            app.remove(1)

            # load should not be called (using cache)
            assert mock_load.call_count == 0, "remove() should use cache"

        # Verify only one todo remains in cache
        assert len(app._cache) == 1
        assert app._cache[0].id == 2

    def test_explicit_flush_saves_to_disk(self, tmp_path: Path) -> None:
        """Test that flush() explicitly saves cache to disk."""
        db = tmp_path / "todo.json"
        app = TodoApp(db_path=str(db))

        # Add todos
        app.add("Task 1")
        app.add("Task 2")

        # Verify file was saved (save is called after each mutation)
        storage = TodoStorage(str(db))
        loaded = storage.load()
        assert len(loaded) == 2

    def test_cache_initialized_on_first_load(self, tmp_path: Path) -> None:
        """Test that cache is initialized lazily on first access."""
        db = tmp_path / "todo.json"

        # Pre-populate the file
        storage = TodoStorage(str(db))
        storage.save([Todo(id=1, text="Existing task", done=False)])

        # Create new app instance
        app = TodoApp(db_path=str(db))

        # Cache should be initialized lazily (not loaded yet)
        # Access via list() should trigger load
        todos = app.list()

        assert len(todos) == 1
        assert todos[0].text == "Existing task"
        # Now cache should be populated
        assert len(app._cache) == 1

    def test_multiple_operations_single_load(self, tmp_path: Path) -> None:
        """Test that multiple operations only load file once (lazy cache)."""
        db = tmp_path / "todo.json"
        app = TodoApp(db_path=str(db))

        # Track storage.load calls
        original_load = app.storage.load
        load_call_count = 0

        def counting_load():
            nonlocal load_call_count
            load_call_count += 1
            return original_load()

        with patch.object(app.storage, "load", side_effect=counting_load):
            # Perform multiple operations
            app.add("Task 1")
            app.add("Task 2")
            app.mark_done(1)
            app.list()
            app.remove(2)

        # With caching, load should only be called once (on first access)
        # After that, all operations use the cache
        assert load_call_count == 1, f"Expected 1 load call with caching, got {load_call_count}"


class TestTodoAppCacheWithExistingData:
    """Test caching behavior when file has existing data."""

    def test_cache_reflects_existing_data(self, tmp_path: Path) -> None:
        """Test that cache properly loads existing data from file."""
        db = tmp_path / "todo.json"

        # Pre-populate with existing data
        storage = TodoStorage(str(db))
        existing_todos = [
            Todo(id=1, text="Existing 1", done=True),
            Todo(id=2, text="Existing 2", done=False),
        ]
        storage.save(existing_todos)

        # Create app and verify cache loads existing data
        app = TodoApp(db_path=str(db))
        todos = app.list()

        assert len(todos) == 2
        assert todos[0].text == "Existing 1"
        assert todos[0].done is True

    def test_new_app_instance_sees_persisted_changes(self, tmp_path: Path) -> None:
        """Test that a new app instance sees changes persisted by previous instance."""
        db = tmp_path / "todo.json"

        # First app instance
        app1 = TodoApp(db_path=str(db))
        app1.add("Task from app1")

        # Second app instance (simulates new process)
        app2 = TodoApp(db_path=str(db))
        todos = app2.list()

        assert len(todos) == 1
        assert todos[0].text == "Task from app1"

"""Regression tests for Issue #6968: TodoApp methods load/save entire file on each operation.

This test file ensures that TodoApp uses in-memory caching to avoid
repeated file I/O operations on each method call.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from flywheel.cli import TodoApp
from flywheel.todo import Todo


def test_todo_app_caches_loaded_todos(tmp_path: Path) -> None:
    """TodoApp should cache loaded todos to avoid repeated file reads.

    Multiple operations on the same TodoApp instance should not trigger
    multiple file reads after the initial load.
    """
    db_path = tmp_path / "test.json"

    # Create initial data
    db_path.write_text(json.dumps([{"id": 1, "text": "Initial", "done": False}]), encoding="utf-8")

    app = TodoApp(db_path=str(db_path))

    # Patch storage.load to track calls
    with patch.object(app.storage, "load", wraps=app.storage.load) as mock_load:
        # Perform multiple operations
        app.list()
        app.list()
        app.list()

        # Should only load once due to caching
        assert mock_load.call_count == 1, (
            f"Expected 1 load call due to caching, got {mock_load.call_count}"
        )


def test_todo_app_caches_and_flushes_on_mutation(tmp_path: Path) -> None:
    """TodoApp should cache data and flush on mutations only."""
    db_path = tmp_path / "test.json"
    db_path.write_text(json.dumps([]), encoding="utf-8")

    app = TodoApp(db_path=str(db_path))

    with (
        patch.object(app.storage, "save", wraps=app.storage.save) as mock_save,
        patch.object(app.storage, "load", wraps=app.storage.load) as mock_load,
    ):
        # Add a todo - should load once and save once
        app.add("Task 1")
        assert mock_load.call_count == 1
        assert mock_save.call_count == 1

        # Add another todo - should NOT load again (uses cache)
        app.add("Task 2")
        assert mock_load.call_count == 1, "Should use cached data, not reload from file"
        assert mock_save.call_count == 2

        # List should also use cache
        app.list()
        assert mock_load.call_count == 1, "List should use cached data"


def test_todo_app_persists_changes_to_file(tmp_path: Path) -> None:
    """Changes should be persisted to file after mutations."""
    db_path = tmp_path / "test.json"
    db_path.write_text(json.dumps([]), encoding="utf-8")

    app = TodoApp(db_path=str(db_path))

    app.add("Task 1")
    app.add("Task 2")
    app.mark_done(1)

    # Verify file was updated
    raw = json.loads(db_path.read_text(encoding="utf-8"))
    assert len(raw) == 2
    assert raw[0]["done"] is True
    assert raw[1]["done"] is False


def test_todo_app_reload_clears_cache(tmp_path: Path) -> None:
    """Reload method should clear cache and reload from file."""
    db_path = tmp_path / "test.json"
    db_path.write_text(json.dumps([{"id": 1, "text": "Initial", "done": False}]), encoding="utf-8")

    app = TodoApp(db_path=str(db_path))

    # Initial load
    todos = app.list()
    assert len(todos) == 1

    # Modify file externally
    db_path.write_text(
        json.dumps([
            {"id": 1, "text": "Initial", "done": False},
            {"id": 2, "text": "External", "done": False},
        ]),
        encoding="utf-8",
    )

    # Without reload, cache is used
    todos = app.list()
    assert len(todos) == 1, "Should use cached data"

    # After reload, fresh data is loaded
    app.reload()
    todos = app.list()
    assert len(todos) == 2, "Should have fresh data after reload"


def test_todo_app_flush_forces_write(tmp_path: Path) -> None:
    """Flush method should force write to file even without mutations."""
    db_path = tmp_path / "test.json"
    db_path.write_text(json.dumps([]), encoding="utf-8")

    app = TodoApp(db_path=str(db_path))

    # Modify cache directly with Todo objects (simulating in-memory modification)
    app._cache = [Todo(id=1, text="Direct", done=False)]

    # Flush should write to file
    app.flush()

    raw = json.loads(db_path.read_text(encoding="utf-8"))
    assert len(raw) == 1
    assert raw[0]["text"] == "Direct"

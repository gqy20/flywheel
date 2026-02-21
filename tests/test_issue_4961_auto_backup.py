"""Tests for automatic backup functionality in TodoStorage.

This test suite verifies that TodoStorage.save() creates automatic backups
of existing files before overwriting them.

Issue: #4961
Feature: Automatic backup before save
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_of_existing_file(tmp_path: Path) -> None:
    """Test that save() creates a backup of existing file before overwriting."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=1, text="new task"), Todo(id=2, text="another task")]
    storage.save(new_todos)

    # Check backup file exists
    backup_path = db.with_suffix(".json.bak")
    assert backup_path.exists(), "Backup file should be created"

    # Verify backup contains original data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original task"


def test_backup_disabled_when_backup_false(tmp_path: Path) -> None:
    """Test that backup=False disables backup creation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save without backup
    new_todos = [Todo(id=1, text="new task")]
    storage.save(new_todos, backup=False)

    # Check backup file does NOT exist
    backup_path = db.with_suffix(".json.bak")
    assert not backup_path.exists(), "Backup file should not be created when backup=False"


def test_backup_failure_does_not_affect_save(tmp_path: Path) -> None:
    """Test that backup failure does not prevent normal save operation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Create a read-only backup directory path that will fail
    # Actually, let's test by making the backup fail but save succeed
    # We'll mock shutil.copy2 to fail
    import shutil
    from unittest.mock import patch

    def failing_copy(*args, **kwargs):
        raise OSError("Simulated backup failure")

    new_todos = [Todo(id=1, text="new task")]
    with patch.object(shutil, "copy2", failing_copy):
        # Save should succeed despite backup failure
        storage.save(new_todos)

    # Verify new data was saved
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new task"


def test_no_backup_for_new_file(tmp_path: Path) -> None:
    """Test that no backup is created when saving to a new file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no existing file to backup
    todos = [Todo(id=1, text="first task")]
    storage.save(todos)

    # Check no backup file exists
    backup_path = db.with_suffix(".json.bak")
    assert not backup_path.exists(), "No backup should be created for new file"


def test_consecutive_saves_update_backup(tmp_path: Path) -> None:
    """Test that consecutive saves update the backup to previous version."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    # Second save - backup should be v1
    todos_v2 = [Todo(id=1, text="version 2")]
    storage.save(todos_v2)

    backup_path = db.with_suffix(".json.bak")
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "version 1"

    # Third save - backup should now be v2
    todos_v3 = [Todo(id=1, text="version 3")]
    storage.save(todos_v3)

    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "version 2"

    # Current file should be v3
    current_content = json.loads(db.read_text(encoding="utf-8"))
    assert current_content[0]["text"] == "version 3"

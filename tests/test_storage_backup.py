"""Tests for file backup mechanism in TodoStorage.

This test suite verifies that TodoStorage.save() creates backups
before overwriting files to prevent accidental data loss.
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_of_existing_file(tmp_path: Path) -> None:
    """Test that save() creates a .bak backup file before overwriting."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - creates initial data
    first_todos = [Todo(id=1, text="first save")]
    storage.save(first_todos)

    # Second save - should create backup
    second_todos = [Todo(id=1, text="second save"), Todo(id=2, text="added")]
    storage.save(second_todos)

    # Verify backup file exists
    backup_path = db.with_suffix(".json.bak")
    assert backup_path.exists(), "Backup file should be created"

    # Verify backup contains first save data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "first save"

    # Verify current file contains second save data
    current_content = json.loads(db.read_text(encoding="utf-8"))
    assert len(current_content) == 2
    assert current_content[0]["text"] == "second save"


def test_first_save_does_not_create_backup(tmp_path: Path) -> None:
    """Test that first save (no existing file) does not create backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no existing file
    todos = [Todo(id=1, text="first")]
    storage.save(todos)

    # No backup should exist
    backup_path = db.with_suffix(".json.bak")
    assert not backup_path.exists(), "Backup should not be created on first save"


def test_backup_disabled_with_config(tmp_path: Path) -> None:
    """Test that backup can be disabled via configuration."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=False)

    # First save
    storage.save([Todo(id=1, text="first")])

    # Second save with backup disabled
    storage.save([Todo(id=1, text="second")])

    # No backup should exist
    backup_path = db.with_suffix(".json.bak")
    assert not backup_path.exists(), "Backup should not be created when disabled"


def test_backup_enabled_by_default(tmp_path: Path) -> None:
    """Test that backup is enabled by default."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))  # No backup parameter

    # First save
    storage.save([Todo(id=1, text="first")])

    # Second save
    storage.save([Todo(id=1, text="second")])

    # Backup should exist by default
    backup_path = db.with_suffix(".json.bak")
    assert backup_path.exists(), "Backup should be enabled by default"


def test_consecutive_saves_update_backup(tmp_path: Path) -> None:
    """Test that consecutive saves update the backup to previous version."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="save1")])

    # Second save
    storage.save([Todo(id=1, text="save2")])

    # Verify backup contains first save
    backup_path = db.with_suffix(".json.bak")
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "save1"

    # Third save
    storage.save([Todo(id=1, text="save3")])

    # Backup should now contain second save
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "save2"

    # Current file should contain third save
    current_content = json.loads(db.read_text(encoding="utf-8"))
    assert current_content[0]["text"] == "save3"

"""Tests for backup/rollback capability for corrupted data files (Issue #2817).

These tests verify that:
1. Save creates a backup file before overwriting existing data
2. Multiple saves rotate backups (only keep 1 .bak file)
3. Restore from backup recovers data when main file is corrupted
4. Load warns about backup availability when JSON is corrupted
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_file(tmp_path) -> None:
    """Test that save() creates .bak file before overwriting existing data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save new data - should create backup of original
    new_todos = [Todo(id=1, text="new task"), Todo(id=2, text="another")]
    storage.save(new_todos)

    # Verify backup file exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created"

    # Verify backup contains original data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original task"


def test_save_creates_backup_on_second_save_only(tmp_path) -> None:
    """Test that first save (when no file exists) doesn't create backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    backup_path = tmp_path / "todo.json.bak"

    # First save - no existing file, so no backup
    todos = [Todo(id=1, text="first")]
    storage.save(todos)

    assert not backup_path.exists(), "No backup should be created on first save"

    # Second save - now backup should be created
    todos2 = [Todo(id=1, text="second")]
    storage.save(todos2)

    assert backup_path.exists(), "Backup should be created on second save"


def test_save_rotates_backup(tmp_path) -> None:
    """Test that multiple saves only keep 1 .bak file (latest backup)."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="v1")])

    # Second save - creates backup of v1
    storage.save([Todo(id=1, text="v2")])
    assert backup_path.exists()

    backup_v2 = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_v2[0]["text"] == "v1"

    # Third save - backup should be v2 (not v1)
    storage.save([Todo(id=1, text="v3")])

    backup_v3 = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_v3[0]["text"] == "v2"


def test_restore_from_backup_success(tmp_path, caplog) -> None:
    """Test that restore_from_backup() restores data from backup file."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Create initial data and save
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="backup me")]
    storage.save(original_todos)

    # Create backup by saving again
    storage.save([Todo(id=1, text="new data")])

    # Verify backup exists with original data
    assert backup_path.exists()
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 2

    # Corrupt main file
    db.write_text("corrupted data", encoding="utf-8")

    # Restore from backup
    result = storage.restore_from_backup()
    assert result is True, "restore_from_backup should return True on success"

    # Verify main file is restored
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "original"
    assert loaded[1].text == "backup me"


def test_restore_from_backup_no_backup(tmp_path) -> None:
    """Test that restore_from_backup() returns False when no backup exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No backup file exists
    result = storage.restore_from_backup()
    assert result is False, "restore_from_backup should return False when no backup"


def test_restore_from_backup_preserves_backup_file(tmp_path) -> None:
    """Test that restore_from_backup() keeps the backup file after restoration."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Create backup
    storage.save([Todo(id=1, text="v1")])
    storage.save([Todo(id=1, text="v2")])

    backup_content_before = backup_path.read_text(encoding="utf-8")

    # Corrupt main file and restore
    db.write_text("corrupt", encoding="utf-8")
    storage.restore_from_backup()

    # Backup should still exist
    assert backup_path.exists()
    assert backup_path.read_text(encoding="utf-8") == backup_content_before


def test_load_json_error_logs_backup_warning(tmp_path, caplog) -> None:
    """Test that load() logs warning when JSON corrupted and backup exists."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Create valid backup
    original_todos = [Todo(id=1, text="backup data")]
    storage.save(original_todos)
    storage.save([Todo(id=1, text="current")])
    assert backup_path.exists()

    # Corrupt main file
    db.write_text('[{"id": 1, "text": "incomplete"', encoding="utf-8")

    # Load should still fail (with ValueError) but log warning about backup
    caplog.set_level(logging.WARNING)
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Check that warning about backup was logged
    assert any("backup" in record.message.lower() for record in caplog.records), \
        "load() should log warning about backup availability"


def test_load_json_no_warning_without_backup(tmp_path, caplog) -> None:
    """Test that load() doesn't log backup warning when no backup exists."""
    db = tmp_path / "todo.json"
    backup_path = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Create file without backup
    storage.save([Todo(id=1, text="data")])
    assert not backup_path.exists()

    # Corrupt main file
    db.write_text("invalid json", encoding="utf-8")

    # Load should fail
    caplog.set_level(logging.WARNING)
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Should not mention backup in warnings (since none exists)
    for record in caplog.records:
        assert "backup" not in record.message.lower(), \
            "Should not mention backup when none exists"


def test_storage_backup_path_property(tmp_path) -> None:
    """Test that TodoStorage has _backup_path property."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    assert hasattr(storage, "_backup_path")
    backup = storage._backup_path
    assert isinstance(backup, Path)
    assert str(backup).endswith("todo.json.bak")

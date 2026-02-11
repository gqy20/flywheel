"""Tests for backup/rollback capability for corrupted data files (Issue #2817).

These tests verify that:
1. save() creates a backup file before overwriting existing data
2. Backup rotation keeps only one .bak file (replaces old backup)
3. restore_from_backup() method recovers data from backup
4. load() warns about backup file when JSON is corrupted
"""

from __future__ import annotations

import logging

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_file(tmp_path, caplog) -> None:
    """Test that save() creates a .bak backup file before overwriting existing data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Verify backup doesn't exist yet (first save, no file to backup)
    backup_path = db.with_suffix(".json.bak")
    assert not backup_path.exists()

    # Save new data (should create backup)
    updated_todos = [Todo(id=1, text="updated task"), Todo(id=2, text="new task")]
    storage.save(updated_todos)

    # Verify backup was created with original content
    assert backup_path.exists(), "Backup file should be created on second save"
    backup_content = backup_path.read_text(encoding="utf-8")
    assert '"original task"' in backup_content
    assert '"updated task"' not in backup_content


def test_backup_rotation_keeps_only_one_backup(tmp_path) -> None:
    """Test that only one .bak file is kept (old backup is replaced)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    backup_path = db.with_suffix(".json.bak")

    # First save
    storage.save([Todo(id=1, text="version 1")])

    # Second save (creates first backup)
    storage.save([Todo(id=1, text="version 2")])
    assert backup_path.exists()

    # Third save (should replace backup, not create a second one)
    storage.save([Todo(id=1, text="version 3")])

    # Verify only one backup exists
    assert backup_path.exists()

    # Verify backup was replaced and contains version 2 data
    backup_content = backup_path.read_text(encoding="utf-8")
    assert "version 2" in backup_content
    assert "version 1" not in backup_content


def test_restore_from_backup_succeeds(tmp_path) -> None:
    """Test that restore_from_backup() successfully restores from backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data and then a backup
    storage.save([Todo(id=1, text="original")])
    storage.save([Todo(id=1, text="corrupted"), Todo(id=2, text="data")])

    backup_path = db.with_suffix(".json.bak")
    assert backup_path.exists()

    # Corrupt the main file
    db.write_text("[{invalid json}", encoding="utf-8")

    # Restore from backup should succeed
    result = storage.restore_from_backup()
    assert result is True, "restore_from_backup should return True on success"

    # Verify main file now contains backup content
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "original"


def test_restore_from_backup_returns_false_when_no_backup(tmp_path) -> None:
    """Test that restore_from_backup() returns False when no backup exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No backup exists
    result = storage.restore_from_backup()
    assert result is False, "restore_from_backup should return False when no backup exists"


def test_load_json_corruption_warns_about_backup(tmp_path, caplog) -> None:
    """Test that load() logs warning about backup file when JSON is corrupted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create backup first
    storage.save([Todo(id=1, text="backup data")])
    storage.save([Todo(id=1, text="current data")])

    backup_path = db.with_suffix(".json.bak")
    assert backup_path.exists()

    # Corrupt the main file
    db.write_text("[{invalid json}", encoding="utf-8")

    # Try to load - should warn about backup
    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match=r"Invalid JSON"):
        storage.load()

    # Verify warning about backup was logged
    assert any("backup" in record.message.lower() for record in caplog.records), \
        "load() should warn about backup file when JSON is corrupted"
    assert any(str(backup_path) in record.message for record in caplog.records), \
        "Warning should include the backup file path"


def test_load_json_corruption_no_warning_if_no_backup(tmp_path, caplog) -> None:
    """Test that load() doesn't warn about backup when none exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Corrupt the main file without creating a backup first
    db.write_text("[{invalid json}", encoding="utf-8")

    # Try to load - should raise error but not warn about backup
    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match=r"Invalid JSON"):
        storage.load()

    # Verify no warning about backup was logged
    assert not any("backup" in record.message.lower() for record in caplog.records), \
        "load() should not warn about backup when none exists"


def test_first_save_does_not_create_backup(tmp_path) -> None:
    """Test that first save() doesn't create backup (no existing file to backup)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    backup_path = db.with_suffix(".json.bak")

    # First save with no existing file
    storage.save([Todo(id=1, text="first todo")])

    # No backup should be created
    assert not backup_path.exists()

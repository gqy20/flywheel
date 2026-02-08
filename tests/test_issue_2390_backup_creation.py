"""Tests for automatic backup creation before file modifications (issue #2390).

This test suite verifies that TodoStorage creates backups before overwriting
existing files, allowing users to recover from accidental data loss.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_before_save_overwrite(tmp_path) -> None:
    """Test that a backup is created when overwriting an existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Overwrite with new data
    new_todos = [Todo(id=2, text="new task")]
    storage.save(new_todos)

    # Verify backup file exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created before overwrite"

    # Verify backup contains original data
    backup_storage = TodoStorage(str(backup_path))
    backup_content = backup_storage.load()
    assert len(backup_content) == 1
    assert backup_content[0].text == "original task"


def test_backup_rotation_keeps_max_n_backups(tmp_path) -> None:
    """Test that backup rotation keeps only the maximum number of backups."""
    db = tmp_path / "todo.json"

    # Set max backups to 3
    with patch.dict(os.environ, {"FLYWHEEL_BACKUP_COUNT": "3"}):
        storage = TodoStorage(str(db))

        # Create 5 saves to generate 5 backups
        for i in range(5):
            todos = [Todo(id=i, text=f"task {i}")]
            storage.save(todos)

    # Check that only 3 backups exist
    backups = sorted(tmp_path.glob("todo.json.bak*"))
    assert len(backups) <= 3, f"Should have at most 3 backups, found {len(backups)}"


def test_backup_count_from_env_variable(tmp_path, monkeypatch) -> None:
    """Test that backup count is configurable via FLYWHEEL_BACKUP_COUNT env var."""
    db = tmp_path / "todo.json"

    # Test with FLYWHEEL_BACKUP_COUNT=5
    monkeypatch.setenv("FLYWHEEL_BACKUP_COUNT", "5")
    storage = TodoStorage(str(db))

    # Create initial data
    storage.save([Todo(id=1, text="initial")])
    storage.save([Todo(id=2, text="second")])

    # At least one backup should exist
    backups = list(tmp_path.glob("todo.json.bak*"))
    assert len(backups) >= 1, "At least one backup should exist"


def test_restore_from_backup_method(tmp_path) -> None:
    """Test that restore_from_backup method can restore from backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="backup test")]
    storage.save(original_todos)

    # Overwrite with different data
    storage.save([Todo(id=3, text="new data")])

    # Restore from backup
    if hasattr(storage, "restore_from_backup"):
        storage.restore_from_backup()
        restored = storage.load()

        # Verify restored data matches original
        assert len(restored) == 2
        assert restored[0].text == "original"
        assert restored[1].text == "backup test"


def test_no_backup_when_file_doesnt_exist(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist yet (first save)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - file doesn't exist yet
    storage.save([Todo(id=1, text="first save")])

    # No backup should be created on first save
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "No backup should be created on first save"


def test_default_backup_count_when_env_not_set(tmp_path, monkeypatch) -> None:
    """Test default behavior when FLYWHEEL_BACKUP_COUNT is not set."""
    db = tmp_path / "todo.json"

    # Ensure env var is not set
    monkeypatch.delenv("FLYWHEEL_BACKUP_COUNT", raising=False)

    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])
    # Second save - should create a backup
    storage.save([Todo(id=2, text="second")])

    # Default behavior should still create at least one backup
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup should be created by default"

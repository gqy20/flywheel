"""Tests for automatic backup creation before file modifications (Issue #2390).

These tests verify that:
1. A .bak backup file is created before overwriting existing data
2. Only N backups are kept (rotation, default 3)
3. FLYWHEEL_BACKUP_COUNT environment variable controls backup count
4. restore_from_backup() method recovers data from backup
5. Backup is created even when save fails after backup
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_file_created_on_save(tmp_path) -> None:
    """Test that .bak.1 backup is created when saving over existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=2, text="new task")]
    storage.save(new_todos)

    # Verify .bak.1 file exists with original data
    backup_path = db.with_suffix(".json.bak.1")
    assert backup_path.exists(), "Backup file should be created"

    # Verify backup contains original data
    backup_storage = TodoStorage(str(backup_path))
    backup_todos = backup_storage.load()
    assert len(backup_todos) == 1
    assert backup_todos[0].text == "original task"


def test_backup_rotation_default_three(tmp_path) -> None:
    """Test that only 3 backups are kept by default (rotation)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create multiple saves to generate multiple backups
    for i in range(5):
        todos = [Todo(id=i, text=f"task {i}")]
        storage.save(todos)

    # List all .bak.N files
    backup_files = sorted(db.parent.glob("*.json.bak.[0-9]*"))

    # Should only have 3 backups (rotation)
    assert len(backup_files) == 3, f"Expected 3 backups, got {len(backup_files)}"


def test_backup_count_from_env_variable(tmp_path) -> None:
    """Test that FLYWHEEL_BACKUP_COUNT environment variable controls backup count."""
    db = tmp_path / "todo.json"

    # Set custom backup count
    with patch.dict(os.environ, {"FLYWHEEL_BACKUP_COUNT": "2"}):
        storage = TodoStorage(str(db))

        # Create multiple saves
        for i in range(5):
            todos = [Todo(id=i, text=f"task {i}")]
            storage.save(todos)

    # List all .bak.N files
    backup_files = sorted(db.parent.glob("*.json.bak.[0-9]*"))

    # Should only have 2 backups as per env variable
    assert len(backup_files) == 2, f"Expected 2 backups, got {len(backup_files)}"


def test_restore_from_backup_method(tmp_path) -> None:
    """Test that restore_from_backup() recovers data from backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save original data
    original_todos = [Todo(id=1, text="backup me"), Todo(id=2, text="another task")]
    storage.save(original_todos)

    # Overwrite with new data (creates backup)
    storage.save([Todo(id=3, text="new data")])

    # Corrupt the main file
    db.write_text("{corrupted json", encoding="utf-8")

    # Restore from backup
    storage.restore_from_backup()

    # Verify restored data matches original
    restored_todos = storage.load()
    assert len(restored_todos) == 2
    assert restored_todos[0].text == "backup me"
    assert restored_todos[1].text == "another task"


def test_backup_created_even_when_save_fails_after_backup(tmp_path) -> None:
    """Test that backup is created even when the subsequent save operation fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="important data")]
    storage.save(original_todos)

    # Mock os.replace to fail after backup was created
    original_replace = os.replace
    call_count = {"count": 0}

    def failing_replace(src, dst):
        call_count["count"] += 1
        # First call should succeed (backup creation uses shutil.copy2)
        # Second call (os.replace for temp file) should fail
        if ".bak" not in str(src):
            raise OSError("Simulated save failure")
        return original_replace(src, dst)

    with (
        patch("flywheel.storage.os.replace", failing_replace),
        pytest.raises(OSError, match="Simulated save failure"),
    ):
        storage.save([Todo(id=2, text="this will fail")])

    # Verify backup was still created
    backup_path = db.with_suffix(".json.bak.1")
    assert backup_path.exists(), "Backup should be created even when save fails"

    # Verify backup has original data
    backup_storage = TodoStorage(str(backup_path))
    backup_todos = backup_storage.load()
    assert len(backup_todos) == 1
    assert backup_todos[0].text == "important data"


def test_no_backup_created_for_new_file(tmp_path) -> None:
    """Test that no backup is created when saving to a non-existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save to non-existing file
    storage.save([Todo(id=1, text="first save")])

    # No backup should be created for new files
    backup_path = db.with_suffix(".json.bak.1")
    assert not backup_path.exists(), "No backup should be created for new files"


def test_restore_from_backup_raises_error_when_no_backup(tmp_path) -> None:
    """Test that restore_from_backup() raises error when no backup exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No backups exist
    with pytest.raises(ValueError, match=r"backup.*not found|no backup"):
        storage.restore_from_backup()

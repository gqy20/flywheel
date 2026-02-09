"""Tests for backup/rollback mechanism in TodoStorage (Issue #2535).

This test suite verifies that TodoStorage can create backups before save
and restore from backup when main file is corrupted.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_when_backup_flag_is_true(tmp_path) -> None:
    """Test that save with backup=True creates a .bak file of existing data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos and save
    original_todos = [Todo(id=1, text="backup test"), Todo(id=2, text="original")]
    storage.save(original_todos)

    # Save with backup=True should create .bak file
    new_todos = [Todo(id=1, text="backup test"), Todo(id=2, text="original"), Todo(id=3, text="new")]
    storage.save(new_todos, backup=True)

    # Verify backup file exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created when backup=True"

    # Verify backup contains the original data (before the new save)
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 2
    assert backup_content[0]["text"] == "backup test"
    assert backup_content[1]["text"] == "original"


def test_save_replaces_existing_backup_on_subsequent_saves(tmp_path) -> None:
    """Test that subsequent saves replace the old backup with new backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save with backup
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    todos_v2 = [Todo(id=1, text="version 2")]
    storage.save(todos_v2, backup=True)

    # Verify backup contains version 1
    backup_path = tmp_path / "todo.json.bak"
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "version 1"

    # Second save with backup
    todos_v3 = [Todo(id=1, text="version 3")]
    storage.save(todos_v3, backup=True)

    # Verify backup now contains version 2 (replaced)
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "version 2"


def test_restore_recovers_data_from_backup_when_main_file_corrupted(tmp_path) -> None:
    """Test that restore() recovers data from .bak when main file has invalid JSON."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos and save with backup
    original_todos = [Todo(id=1, text="restore test"), Todo(id=2, text="will be restored")]
    storage.save(original_todos)
    storage.save([Todo(id=1, text="new")], backup=True)  # This creates backup of original_todos

    # Corrupt the main file
    db.write_text("invalid json {corrupted", encoding="utf-8")

    # Restore from backup
    storage.restore()

    # Verify main file now contains valid data from backup
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "restore test"
    assert loaded[1].text == "will be restored"


def test_save_succeeds_when_main_file_exists_but_backup_missing(tmp_path) -> None:
    """Test that save works when main file exists but no backup exists yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos (no backup yet)
    original_todos = [Todo(id=1, text="no backup yet")]
    storage.save(original_todos)

    # Save with backup=True should work even though no previous backup exists
    new_todos = [Todo(id=1, text="no backup yet"), Todo(id=2, text="new todo")]
    storage.save(new_todos, backup=True)

    # Verify main file has the new data
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "no backup yet"
    assert loaded[1].text == "new todo"


def test_backup_removed_after_successful_save_when_retention_zero(tmp_path) -> None:
    """Test that backup is cleaned up when cleanup_backup(retention=0) is called."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos and save with backup
    original_todos = [Todo(id=1, text="cleanup test")]
    storage.save(original_todos)
    storage.save([Todo(id=2, text="new")], backup=True)

    # Verify backup exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists()

    # Clean up backup with retention=0 (remove immediately)
    storage.cleanup_backup(retention=0)

    # Verify backup is removed
    assert not backup_path.exists(), "Backup should be removed when retention=0"


def test_restore_raises_error_when_no_backup_exists(tmp_path) -> None:
    """Test that restore() raises error when no backup file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Try to restore when no backup exists
    with pytest.raises(FileNotFoundError, match="No backup file found"):
        storage.restore()


def test_save_without_backup_does_not_create_backup_file(tmp_path) -> None:
    """Test that save without backup parameter does not create .bak file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save without backup (default behavior)
    todos = [Todo(id=1, text="no backup")]
    storage.save(todos)

    # Verify no backup file was created
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "No backup file should be created when backup is not specified"

"""Tests for backup/rollback mechanism in TodoStorage (issue #2535).

This test suite verifies that TodoStorage can create backups before save
and restore from backup when needed.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_when_save_with_backup_true(tmp_path) -> None:
    """Test that save() with backup=True creates a .bak file of existing data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save with backup=True
    new_todos = [Todo(id=1, text="original task"), Todo(id=2, text="new task")]
    storage.save(new_todos, backup=True)

    # Verify .bak file was created
    backup_path = db.with_suffix(db.suffix + ".bak")
    assert backup_path.exists(), "Backup file should be created when backup=True"

    # Verify backup contains the original data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original task"


def test_backup_is_replaced_on_subsequent_saves(tmp_path) -> None:
    """Test that old backup is replaced with new backup on subsequent saves."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    # First save with backup
    todos_v2 = [Todo(id=1, text="version 2")]
    storage.save(todos_v2, backup=True)
    # Capture the backup content BEFORE the second save
    backup_content_v1 = json.loads(storage._backup_path.read_text(encoding="utf-8"))

    # Second save with backup
    todos_v3 = [Todo(id=1, text="version 3")]
    storage.save(todos_v3, backup=True)
    backup_content_v2 = json.loads(storage._backup_path.read_text(encoding="utf-8"))

    # Verify backup was replaced (contains v2 data, not v1)
    assert backup_content_v2[0]["text"] == "version 2"
    assert backup_content_v1[0]["text"] == "version 1"


def test_restore_recovers_from_backup_when_main_corrupted(tmp_path) -> None:
    """Test that restore() recovers data from .bak when main file has invalid JSON."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data (without backup - just to have a file)
    original_todos = [Todo(id=1, text="backup task"), Todo(id=2, text="another task")]
    storage.save(original_todos)

    # Now create a backup explicitly
    storage.backup_file()

    # Corrupt the main file
    db.write_text("invalid json{corrupted", encoding="utf-8")

    # Verify main file is corrupted
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Restore from backup
    storage.restore()

    # Verify main file now has the backed up data
    restored = storage.load()
    assert len(restored) == 2
    assert restored[0].text == "backup task"
    assert restored[1].text == "another task"


def test_save_succeeds_when_main_exists_but_no_backup(tmp_path) -> None:
    """Test that save() succeeds when main file exists but .bak is missing."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data without backup
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Explicitly verify no backup exists yet
    assert not storage._backup_path.exists()

    # Save should succeed and create backup even without prior backup
    new_todos = [Todo(id=1, text="original"), Todo(id=2, text="new")]
    storage.save(new_todos, backup=True)

    # Verify main file was updated
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "original"
    assert loaded[1].text == "new"


def test_restore_raises_when_no_backup_exists(tmp_path) -> None:
    """Test that restore() raises appropriate error when no backup file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Verify no backup file exists
    assert not storage._backup_path.exists()

    # restore() should raise FileNotFoundError
    with pytest.raises(FileNotFoundError, match="No backup file"):
        storage.restore()


def test_save_without_backup_does_not_create_backup_file(tmp_path) -> None:
    """Test that save() without backup parameter does not create .bak file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save without backup (default behavior)
    new_todos = [Todo(id=1, text="updated")]
    storage.save(new_todos)

    # Verify .bak file was NOT created
    assert not storage._backup_path.exists(), "Backup file should not be created when backup=False"

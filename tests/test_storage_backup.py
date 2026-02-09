"""Tests for backup/rollback mechanism in TodoStorage save operations.

This test suite verifies that TodoStorage.save() can create backups
and TodoStorage.restore() can recover from backups when needed.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_when_backup_enabled(tmp_path) -> None:
    """Test that save with backup=True creates a .bak file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Save with backup=True
    new_todos = [Todo(id=1, text="modified"), Todo(id=2, text="updated")]
    storage.save(new_todos, backup=True)

    # Verify backup file exists
    backup_path = storage._backup_path
    assert backup_path.exists(), "Backup file should be created"

    # Verify backup contains original data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 2
    assert backup_content[0]["text"] == "original"
    assert backup_content[1]["text"] == "data"

    # Verify main file contains new data
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "modified"
    assert loaded[1].text == "updated"


def test_save_replaces_old_backup_on_subsequent_saves(tmp_path) -> None:
    """Test that subsequent saves replace the old backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save with backup
    todos1 = [Todo(id=1, text="first")]
    storage.save(todos1)

    todos2 = [Todo(id=1, text="second")]
    storage.save(todos2, backup=True)
    backup_content_after_second = json.loads(storage._backup_path.read_text(encoding="utf-8"))
    assert backup_content_after_second[0]["text"] == "first"

    # Second save with backup
    todos3 = [Todo(id=1, text="third")]
    storage.save(todos3, backup=True)

    # Verify backup was replaced
    backup_content_after_third = json.loads(storage._backup_path.read_text(encoding="utf-8"))
    assert backup_content_after_third[0]["text"] == "second"
    assert backup_content_after_third[0]["text"] != "first"


def test_restore_recovers_from_backup_when_main_file_corrupted(tmp_path) -> None:
    """Test that restore recovers data from .bak when main file is corrupted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data and backup
    original_todos = [Todo(id=1, text="backup data"), Todo(id=2, text="should be restored")]
    storage.save(original_todos)
    storage.save([Todo(id=3, text="new")], backup=True)

    # Corrupt the main file
    db.write_text("corrupted json {{}", encoding="utf-8")

    # Verify main file is corrupted
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Restore from backup
    storage.restore()

    # Verify main file now contains backup data
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "backup data"
    assert loaded[1].text == "should be restored"


def test_restore_raises_when_no_backup_exists(tmp_path) -> None:
    """Test that restore raises OSError when no backup exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data without backup
    todos = [Todo(id=1, text="data")]
    storage.save(todos)

    # Try to restore without backup
    with pytest.raises(OSError, match="No backup file"):
        storage.restore()


def test_save_without_backup_parameter_skips_backup(tmp_path) -> None:
    """Test that save without backup=True does not create a backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save without backup parameter (default is False)
    new_todos = [Todo(id=1, text="new")]
    storage.save(new_todos)

    # Verify backup file does not exist
    assert not storage._backup_path.exists()


def test_save_with_explicit_backup_false_skips_backup(tmp_path) -> None:
    """Test that save with backup=False explicitly does not create a backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save with backup=False
    new_todos = [Todo(id=1, text="new")]
    storage.save(new_todos, backup=False)

    # Verify backup file does not exist
    assert not storage._backup_path.exists()


def test_save_fails_when_backup_write_fails_preserves_original(tmp_path) -> None:
    """Test that if backup write fails, original file is preserved and save raises."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)
    original_content = db.read_text(encoding="utf-8")

    # Simulate backup write failure
    def failing_copy(*args, **kwargs):
        raise OSError("Simulated backup write failure")

    with (
        patch("shutil.copy", failing_copy),
        pytest.raises(OSError, match="Simulated backup write failure"),
    ):
        storage.save([Todo(id=3, text="new")], backup=True)

    # Verify original file is unchanged
    assert db.read_text(encoding="utf-8") == original_content

    # Verify we can still load the original data
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "original"
    assert loaded[1].text == "data"


def test_backup_path_property_returns_correct_path(tmp_path) -> None:
    """Test that _backup_path property returns the correct backup file path."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Verify backup path is correct
    assert storage._backup_path == tmp_path / "todo.json.bak"


def test_save_with_backup_creates_directory_if_needed(tmp_path) -> None:
    """Test that backup creation works when parent directory doesn't exist."""
    db = tmp_path / "subdir" / "todo.json"
    storage = TodoStorage(str(db))

    # First save to create initial file (no backup yet since no file exists)
    todos1 = [Todo(id=1, text="initial")]
    storage.save(todos1)

    # Second save with backup - should create backup in the same directory
    todos2 = [Todo(id=2, text="updated")]
    storage.save(todos2, backup=True)

    # Verify both main and backup files exist
    assert db.exists()
    assert storage._backup_path.exists()


def test_restore_removes_backup_after_successful_restore(tmp_path) -> None:
    """Test that restore removes the backup file after successful restore."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create data and backup
    original_todos = [Todo(id=1, text="backup data")]
    storage.save(original_todos)
    storage.save([Todo(id=2, text="new")], backup=True)

    # Corrupt main file
    db.write_text("corrupted", encoding="utf-8")

    # Restore from backup
    storage.restore()

    # Verify backup was removed
    assert not storage._backup_path.exists()

    # Verify main file has restored data
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "backup data"

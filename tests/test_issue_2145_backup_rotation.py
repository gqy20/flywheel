"""Regression tests for Issue #2145: File backup/rotation before overwrites.

This test file ensures that TodoStorage can create backups of the existing
file before overwriting, protecting against data loss from bugs or accidental
deletions.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_first_save_creates_no_backup_when_no_existing_file(tmp_path) -> None:
    """Test that first save creates no backup when target file doesn't exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    todos = [Todo(id=1, text="first todo")]
    storage.save(todos)

    # Main file should be created
    assert db.exists()
    # No backup file should be created on first save
    backup = db.parent / (db.name + ".bak")
    assert not backup.exists()


def test_second_save_creates_backup_with_previous_content(tmp_path) -> None:
    """Test that second save creates .bak file with previous content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # First save
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    # Second save - should create backup
    todos_v2 = [Todo(id=1, text="version 2")]
    storage.save(todos_v2)

    # Backup should exist
    backup = db.parent / (db.name + ".bak")
    assert backup.exists()

    # Backup should contain the first version
    storage_backup = TodoStorage(str(backup))
    loaded_backup = storage_backup.load()
    assert len(loaded_backup) == 1
    assert loaded_backup[0].text == "version 1"

    # Main file should contain the second version
    loaded_main = storage.load()
    assert len(loaded_main) == 1
    assert loaded_main[0].text == "version 2"


def test_third_save_overwrites_backup_with_second_version(tmp_path) -> None:
    """Test that third save overwrites .bak with second version (rotation)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # First save
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    # Second save - creates backup of v1
    todos_v2 = [Todo(id=1, text="version 2")]
    storage.save(todos_v2)

    # Third save - should overwrite backup with v2
    todos_v3 = [Todo(id=1, text="version 3")]
    storage.save(todos_v3)

    # Backup should now contain version 2, not version 1
    backup = db.parent / (db.name + ".bak")
    storage_backup = TodoStorage(str(backup))
    loaded_backup = storage_backup.load()
    assert len(loaded_backup) == 1
    assert loaded_backup[0].text == "version 2"

    # Main file should contain version 3
    loaded_main = storage.load()
    assert len(loaded_main) == 1
    assert loaded_main[0].text == "version 3"


def test_backup_disabled_by_default(tmp_path) -> None:
    """Test that backups are disabled by default (enable_backups=False)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))  # Default: enable_backups=False

    # First save
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    # Second save - should NOT create backup
    todos_v2 = [Todo(id=1, text="version 2")]
    storage.save(todos_v2)

    # Backup should not exist
    backup = db.parent / (db.name + ".bak")
    assert not backup.exists()


def test_save_succeeds_even_when_backup_creation_fails(tmp_path) -> None:
    """Test that save succeeds even when backup creation fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # First save
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    # Mock shutil.copy2 to fail
    def failing_copy2(src, dst, **kwargs):
        raise OSError("Simulated backup failure")

    with patch("flywheel.storage.shutil.copy2", failing_copy2):
        # Second save should still succeed despite backup failure
        todos_v2 = [Todo(id=1, text="version 2")]
        storage.save(todos_v2)  # Should not raise

    # Main file should be updated
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "version 2"


def test_backup_preserves_metadata_using_shutil_copy2(tmp_path) -> None:
    """Test that backup uses shutil.copy2 to preserve file metadata."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # First save
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    # Track if shutil.copy2 was called
    copy2_calls = []
    original_copy2 = __import__("shutil").copy2

    def tracking_copy2(src, dst, **kwargs):
        copy2_calls.append((src, dst))
        return original_copy2(src, dst, **kwargs)

    with patch("flywheel.storage.shutil.copy2", tracking_copy2):
        # Second save
        todos_v2 = [Todo(id=1, text="version 2")]
        storage.save(todos_v2)

    # Verify shutil.copy2 was called for backup
    assert len(copy2_calls) == 1
    assert copy2_calls[0][0] == db
    assert str(copy2_calls[0][1]).endswith(".bak")


def test_backup_with_multiple_todos_preserves_all_data(tmp_path) -> None:
    """Test that backup preserves all todos including complex data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # First save with multiple todos
    todos_v1 = [
        Todo(id=1, text="task 1", done=False),
        Todo(id=2, text="task with unicode: 你好", done=True),
        Todo(id=3, text="task with \"quotes\"", done=False),
    ]
    storage.save(todos_v1)

    # Second save
    todos_v2 = [Todo(id=4, text="new task")]
    storage.save(todos_v2)

    # Backup should contain all todos from v1 with correct state
    backup = db.parent / (db.name + ".bak")
    storage_backup = TodoStorage(str(backup))
    loaded_backup = storage_backup.load()
    assert len(loaded_backup) == 3
    assert loaded_backup[0].text == "task 1"
    assert loaded_backup[0].done is False
    assert loaded_backup[1].text == "task with unicode: 你好"
    assert loaded_backup[1].done is True
    assert loaded_backup[2].text == 'task with "quotes"'
    assert loaded_backup[2].done is False

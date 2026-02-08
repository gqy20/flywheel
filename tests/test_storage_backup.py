"""Tests for file backup/rotation feature in TodoStorage.

This test suite verifies that TodoStorage.save() creates backups
before overwriting, allowing data recovery from accidental mistakes.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_with_backup_enabled_creates_backup_file(tmp_path) -> None:
    """Test that save with backup=True creates a .bak.1 file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True, backup_count=3)

    # Create initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=1, text="modified")]
    storage.save(new_todos)

    # Verify backup file was created
    backup_path = db.parent / f"{db.name}.1.bak"
    assert backup_path.exists(), "Backup file should be created"

    # Verify backup contains original content
    backup_storage = TodoStorage(str(backup_path))
    loaded_backup = backup_storage.load()
    assert len(loaded_backup) == 2
    assert loaded_backup[0].text == "original"
    assert loaded_backup[1].text == "data"

    # Verify main file has new content
    loaded_main = storage.load()
    assert len(loaded_main) == 1
    assert loaded_main[0].text == "modified"


def test_save_without_backup_does_not_create_backup_file(tmp_path) -> None:
    """Test that save with backup=False (default) does not create backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=False)

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save new data
    new_todos = [Todo(id=1, text="modified")]
    storage.save(new_todos)

    # Verify no backup file was created
    backup_path = db.parent / f"{db.name}.1.bak"
    assert not backup_path.exists(), "No backup file should be created when backup=False"


def test_rotating_backup_keeps_only_n_most_recent_backups(tmp_path) -> None:
    """Test that rotating backup deletes old backups beyond backup_count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True, backup_count=3)

    # Save multiple times to create more backups than backup_count
    for i in range(5):
        todos = [Todo(id=1, text=f"version-{i}")]
        storage.save(todos)

    # Should only have 3 backups (backup_count=3)
    backup_1 = db.parent / f"{db.name}.1.bak"
    backup_2 = db.parent / f"{db.name}.2.bak"
    backup_3 = db.parent / f"{db.name}.3.bak"
    backup_4 = db.parent / f"{db.name}.4.bak"
    backup_5 = db.parent / f"{db.name}.5.bak"

    # Only backups 1-3 should exist (most recent)
    assert backup_1.exists(), "Most recent backup .1.bak should exist"
    assert backup_2.exists(), "Second recent backup .2.bak should exist"
    assert backup_3.exists(), "Third recent backup .3.bak should exist"
    assert not backup_4.exists(), "Old backup .4.bak should be deleted"
    assert not backup_5.exists(), "Old backup .5.bak should be deleted"


def test_backup_file_content_matches_pre_save_content(tmp_path) -> None:
    """Test that backup file contains the exact content before new save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True, backup_count=2)

    # Create specific data
    original_todos = [
        Todo(id=1, text="task one", done=False),
        Todo(id=2, text="task two", done=True),
        Todo(id=3, text="task three"),
    ]
    storage.save(original_todos)

    # Save different data
    new_todos = [Todo(id=1, text="new task")]
    storage.save(new_todos)

    # Verify backup has exact original data
    backup_path = db.parent / f"{db.name}.1.bak"
    backup_storage = TodoStorage(str(backup_path))
    loaded_backup = backup_storage.load()

    assert len(loaded_backup) == 3
    assert loaded_backup[0].id == 1
    assert loaded_backup[0].text == "task one"
    assert loaded_backup[0].done is False
    assert loaded_backup[1].id == 2
    assert loaded_backup[1].text == "task two"
    assert loaded_backup[1].done is True
    assert loaded_backup[2].id == 3
    assert loaded_backup[2].text == "task three"


def test_backup_created_only_when_file_exists(tmp_path) -> None:
    """Test that backup is only created when file already exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True, backup_count=2)

    # First save - no file exists yet, so no backup should be created
    first_todos = [Todo(id=1, text="first save")]
    storage.save(first_todos)

    backup_path = db.parent / f"{db.name}.1.bak"
    assert not backup_path.exists(), "No backup should be created on first save (no existing file)"

    # Second save - file exists, backup should be created
    second_todos = [Todo(id=1, text="second save")]
    storage.save(second_todos)

    assert backup_path.exists(), "Backup should be created when file exists"


def test_backup_naming_follows_expected_pattern(tmp_path) -> None:
    """Test that backup files follow the pattern: .todo.json.1.bak, .todo.json.2.bak, etc."""
    db = tmp_path / "custom.json"
    storage = TodoStorage(str(db), backup=True, backup_count=2)

    # Create multiple backups
    for i in range(3):
        todos = [Todo(id=1, text=f"save-{i}")]
        storage.save(todos)

    # Verify naming pattern
    backup_1 = db.parent / "custom.json.1.bak"
    backup_2 = db.parent / "custom.json.2.bak"

    assert backup_1.exists(), "Backup .1.bak should exist with correct naming"
    assert backup_2.exists(), "Backup .2.bak should exist with correct naming"


def test_default_backup_count_is_three(tmp_path) -> None:
    """Test that default backup_count is 3 when backup=True is specified."""
    db = tmp_path / "todo.json"
    # Create storage with backup=True but no explicit backup_count
    storage = TodoStorage(str(db), backup=True)

    # Check that backup_count defaults to 3
    assert storage.backup_count == 3, "Default backup_count should be 3"

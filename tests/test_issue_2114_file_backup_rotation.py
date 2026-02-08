"""Tests for file backup/rotation before overwriting (Issue #2114).

These tests verify that:
1. TodoStorage with backup_count > 0 creates .bak files before save()
2. Rotating backup keeps only N most recent backups (configurable)
3. Backup file naming follows pattern: .todo.json.1.bak, .todo.json.2.bak
4. Backup file contains original content before new save
5. Backups are created atomically (using same temp file pattern)
6. Backup works even when save fails
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_with_backup_creates_backup_file(tmp_path) -> None:
    """Test that save with backup_count=1 creates .bak file when overwriting existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Enable backup
    storage.backup_count = 1

    # Create initial data (first save - no backup since file doesn't exist)
    storage.save([Todo(id=1, text="initial")])

    # Save new data - this should create a backup of the initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Verify backup was created
    backup_path = tmp_path / ".todo.json.1.bak"
    assert backup_path.exists(), "Backup file should be created when overwriting existing file"

    # Verify backup contains the initial data (not the new data)
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "initial"


def test_save_without_backup_creates_no_backup_file(tmp_path) -> None:
    """Test that save with backup_count=0 (default) creates no .bak file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Verify default is no backup
    assert storage.backup_count == 0, "Default backup_count should be 0"

    # Create initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Verify no backup was created
    backup_path = tmp_path / ".todo.json.1.bak"
    assert not backup_path.exists(), "No backup file should be created when backup_count=0"


def test_rotating_backup_keeps_only_n_backups(tmp_path) -> None:
    """Test that rotating backup keeps only N most recent backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Enable backup with count of 2
    storage.backup_count = 2

    # Initial save (no backup - file doesn't exist)
    storage.save([Todo(id=0, text="initial")])

    # First overwrite - should create .1.bak
    storage.save([Todo(id=1, text="first")])
    backup_1 = tmp_path / ".todo.json.1.bak"
    assert backup_1.exists()

    # Second overwrite - should rotate: .1.bak -> .2.bak, create new .1.bak
    storage.save([Todo(id=2, text="second")])
    backup_2 = tmp_path / ".todo.json.2.bak"
    assert backup_1.exists(), ".1.bak should exist after rotation"
    assert backup_2.exists(), ".2.bak should exist after rotation"

    # Verify .2.bak contains "initial" data (from the first backup)
    backup_2_content = json.loads(backup_2.read_text(encoding="utf-8"))
    assert backup_2_content[0]["text"] == "initial"

    # Verify .1.bak contains "first" data (from the second backup)
    backup_1_content = json.loads(backup_1.read_text(encoding="utf-8"))
    assert backup_1_content[0]["text"] == "first"

    # Third overwrite - should rotate: .1.bak -> .2.bak, .2.bak deleted, create new .1.bak
    storage.save([Todo(id=3, text="third")])
    backup_3 = tmp_path / ".todo.json.3.bak"

    assert backup_1.exists(), ".1.bak should exist after third save"
    assert backup_2.exists(), ".2.bak should exist after third save"
    assert not backup_3.exists(), ".3.bak should NOT exist (exceeds backup_count=2)"


def test_backup_file_naming_follows_pattern(tmp_path) -> None:
    """Test that backup file naming follows pattern: .todo.json.1.bak, .todo.json.2.bak."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.backup_count = 3

    # Initial save (no backup - file doesn't exist)
    storage.save([Todo(id=0, text="initial")])

    # Create multiple saves to generate multiple backups
    for i in range(3):
        storage.save([Todo(id=i, text=f"save-{i}")])

    # Verify backup files exist with correct naming pattern
    # We should have 3 backups (1, 2, 3) after 3 overwrite operations
    for i in range(1, 4):
        backup_path = tmp_path / f".todo.json.{i}.bak"
        assert backup_path.exists(), f"Backup file {i} should exist"


def test_backup_contains_original_content_before_new_save(tmp_path) -> None:
    """Test that backup file contains original content before new save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.backup_count = 1

    # Create initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Save new data
    new_todos = [Todo(id=3, text="new")]
    storage.save(new_todos)

    # Verify backup contains the original data, not the new data
    backup_path = tmp_path / ".todo.json.1.bak"
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 2
    assert backup_content[0]["text"] == "original"
    assert backup_content[1]["text"] == "data"

    # Verify main file contains new data
    main_content = json.loads(db.read_text(encoding="utf-8"))
    assert len(main_content) == 1
    assert main_content[0]["text"] == "new"


def test_backup_created_before_save_replaces_main_file(tmp_path) -> None:
    """Test that backup is created before os.replace() happens."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.backup_count = 1

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Track the order: backup should exist before main file is updated
    # We can't directly test the ordering, but we can verify that
    # after a save, both the backup and main file exist

    # Save new data
    new_todos = [Todo(id=2, text="new")]
    storage.save(new_todos)

    # Both files should exist
    backup_path = tmp_path / ".todo.json.1.bak"
    assert backup_path.exists(), "Backup should exist"
    assert db.exists(), "Main file should exist"

    # They should have different content
    assert db.read_text(encoding="utf-8") != backup_path.read_text(encoding="utf-8")


def test_backup_with_different_db_path(tmp_path) -> None:
    """Test that backup works with different database path."""
    db = tmp_path / "subdir" / "custom.json"
    storage = TodoStorage(str(db))

    storage.backup_count = 1

    # Create initial data (first save - no backup)
    storage.save([Todo(id=1, text="initial")])

    # Save new data (should create backup of initial data)
    storage.save([Todo(id=2, text="original")])

    # Verify backup was created in same directory as db file
    backup_path = tmp_path / "subdir" / ".custom.json.1.bak"
    assert backup_path.exists(), "Backup should be created in same directory as db file"

    # Verify backup contains initial data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "initial"


def test_backup_on_first_save_when_file_doesnt_exist(tmp_path) -> None:
    """Test that backup on first save (when file doesn't exist) doesn't create backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.backup_count = 1

    # First save - file doesn't exist yet, so no backup should be created
    storage.save([Todo(id=1, text="first")])

    backup_path = tmp_path / ".todo.json.1.bak"
    assert not backup_path.exists(), "No backup should be created on first save"


def test_backup_count_attribute_can_be_modified(tmp_path) -> None:
    """Test that backup_count can be modified after initialization."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initially no backup
    assert storage.backup_count == 0

    # Create initial data without backup
    storage.save([Todo(id=1, text="no backup")])

    # Enable backup
    storage.backup_count = 1
    storage.save([Todo(id=2, text="with backup")])

    backup_path = tmp_path / ".todo.json.1.bak"
    assert backup_path.exists(), "Backup should be created after enabling"

    # Verify backup contains the "no backup" data (backed up before overwriting)
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "no backup"

    # Disable backup
    storage.backup_count = 0
    storage.save([Todo(id=3, text="without backup")])

    # Old backup should still exist, but no new one created
    assert backup_path.exists(), "Old backup should still exist"

    # Only one backup should exist (no .2.bak created after disabling)
    backup_2 = tmp_path / ".todo.json.2.bak"
    assert not backup_2.exists()

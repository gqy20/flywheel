"""Tests for backup creation feature - Candidate #2: Numeric rotation (Issue #2494).

This candidate uses a numeric rotation scheme:
- First backup: .todo.json.bak
- Second backup: .todo.json.bak.1 (old .bak becomes .bak.1)
- Third backup: .todo.json.bak.2 (old .bak.1 becomes .bak.2)
- etc.

These tests verify that:
1. Backups are created before overwriting existing files
2. Only N most recent backups are kept (configurable, default 3)
3. list_backups() shows available backup files
4. restore_from_backup() can restore data from backup
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_on_save(tmp_path) -> None:
    """Test that a .bak backup file is created when saving to existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos and save
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save new todos (should create backup of original)
    new_todos = [Todo(id=1, text="new task", done=True)]
    storage.save(new_todos)

    # Verify backup file was created
    backup = db.parent / ".todo.json.bak"
    assert backup.exists(), "Expected .bak file to be created"

    # Verify backup contains original data
    backup_content = json.loads(backup.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original task"


def test_backup_not_created_on_first_save(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no file exists yet
    todos = [Todo(id=1, text="first todo")]
    storage.save(todos)

    # Verify no backup files were created
    backup = db.parent / ".todo.json.bak"
    assert not backup.exists(), "Expected no .bak file on first save"


def test_backup_rotation_keeps_default_three_backups(tmp_path) -> None:
    """Test that only 3 most recent backups are kept by default."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create multiple saves to generate backups
    # First save doesn't create backup (no existing file)
    # Each subsequent save creates a backup of the previous file
    for i in range(5):
        todos = [Todo(id=1, text=f"version {i}")]
        storage.save(todos)

    # Check backup files exist with numeric rotation
    # With max_backups=3, we should have .bak, .bak.1, .bak.2
    # They should contain versions 3, 2, 1 respectively (version 0 was cleaned up)
    backup_base = db.parent / ".todo.json.bak"
    backup_1 = db.parent / ".todo.json.bak.1"
    backup_2 = db.parent / ".todo.json.bak.2"
    backup_3 = db.parent / ".todo.json.bak.3"

    assert backup_base.exists(), ".bak should exist (most recent)"
    assert backup_1.exists(), ".bak.1 should exist"
    assert backup_2.exists(), ".bak.2 should exist"
    assert not backup_3.exists(), ".bak.3 should not exist (exceeds max_backups=3)"

    # Verify the backups are the 3 most recent ones
    # .bak contains version 3, .bak.1 contains version 2, .bak.2 contains version 1
    base_content = json.loads(backup_base.read_text(encoding="utf-8"))
    assert base_content[0]["text"] == "version 3"

    backup_1_content = json.loads(backup_1.read_text(encoding="utf-8"))
    assert backup_1_content[0]["text"] == "version 2"

    backup_2_content = json.loads(backup_2.read_text(encoding="utf-8"))
    assert backup_2_content[0]["text"] == "version 1"


def test_backup_rotation_respects_custom_limit(tmp_path) -> None:
    """Test that backup rotation respects custom max_backups setting."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=2)

    # Create multiple saves to generate backups
    for i in range(5):
        todos = [Todo(id=1, text=f"version {i}")]
        storage.save(todos)

    # With max_backups=2, we should have .bak and .bak.1 only
    backup_base = db.parent / ".todo.json.bak"
    backup_1 = db.parent / ".todo.json.bak.1"
    backup_2 = db.parent / ".todo.json.bak.2"

    assert backup_base.exists(), ".bak should exist"
    assert backup_1.exists(), ".bak.1 should exist"
    assert not backup_2.exists(), ".bak.2 should not exist (exceeds max_backups=2)"


def test_list_backups_returns_available_backups(tmp_path) -> None:
    """Test that list_backups() returns list of backup file paths."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data and then several saves to generate backups
    storage.save([Todo(id=1, text="v0")])
    for i in range(1, 4):
        storage.save([Todo(id=1, text=f"v{i}")])

    # List backups
    backups = storage.list_backups()

    # Should return 3 backup paths (with max_backups=3)
    assert len(backups) == 3
    # All should be Path objects
    assert all(isinstance(b, type(db)) for b in backups)
    # All should have .bak in name
    assert all(".bak" in str(b) for b in backups)


def test_list_backups_returns_empty_list_when_no_backups(tmp_path) -> None:
    """Test that list_backups() returns empty list when no backups exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No saves yet, so no backups
    backups = storage.list_backups()
    assert backups == []


def test_restore_from_backup_restores_data(tmp_path) -> None:
    """Test that restore_from_backup() correctly restores data from backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create original data (first save - no backup created yet)
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="backup me")]
    storage.save(original_todos)

    # Save again to create a backup of the original data
    storage.save([Todo(id=1, text="new version that will be corrupted")])

    # Corrupt the current file with bad data
    db.write_text('{"invalid": "json", "structure": []}', encoding="utf-8")

    # Get the backup file (should contain original data)
    backups = storage.list_backups()
    assert len(backups) == 1

    # Restore from backup
    storage.restore_from_backup(backups[0])

    # Verify data was restored correctly
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "original"
    assert loaded[1].text == "backup me"


def test_restore_from_backup_creates_new_file_if_missing(tmp_path) -> None:
    """Test that restore_from_backup() creates main file if it doesn't exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create original data and then a second save to generate a backup
    original_todos = [Todo(id=1, text="restored")]
    storage.save(original_todos)
    storage.save([Todo(id=1, text="newer")])  # This creates backup of "restored"

    # Delete the main file
    db.unlink()

    # Get the backup file
    backups = storage.list_backups()
    assert len(backups) == 1

    # Restore from backup
    storage.restore_from_backup(backups[0])

    # Verify main file was recreated with correct data
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "restored"


def test_restore_from_nonexistent_backup_raises_error(tmp_path) -> None:
    """Test that restoring from non-existent backup raises FileNotFoundError."""
    import pytest

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    fake_backup = tmp_path / ".todo.json.bak.fake"

    with pytest.raises(FileNotFoundError, match="not found"):
        storage.restore_from_backup(fake_backup)


def test_restore_from_invalid_json_backup_raises_error(tmp_path) -> None:
    """Test that restoring from backup with invalid JSON raises ValueError."""
    import pytest

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a backup file with invalid JSON
    invalid_backup = tmp_path / ".todo.json.bak"
    invalid_backup.write_text("{invalid json}", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid JSON"):
        storage.restore_from_backup(invalid_backup)


def test_backup_ordering_preserves_recency(tmp_path) -> None:
    """Test that list_backups returns backups in correct order (oldest to newest)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create sequence of saves
    storage.save([Todo(id=1, text="first")])
    storage.save([Todo(id=1, text="second")])
    storage.save([Todo(id=1, text="third")])
    storage.save([Todo(id=1, text="fourth")])

    backups = storage.list_backups()
    assert len(backups) == 3  # max_backups=3

    # list_backups returns oldest to newest
    # [0] = .bak.2 (oldest), [1] = .bak.1, [2] = .bak (newest)
    content_0 = json.loads(backups[0].read_text(encoding="utf-8"))
    content_1 = json.loads(backups[1].read_text(encoding="utf-8"))
    content_2 = json.loads(backups[2].read_text(encoding="utf-8"))

    assert content_0[0]["text"] == "first"  # oldest
    assert content_1[0]["text"] == "second"
    assert content_2[0]["text"] == "third"  # newest (before current "fourth")

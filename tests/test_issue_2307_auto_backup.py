"""Tests for automatic backup before save feature (issue #2307).

This test suite verifies that TodoStorage.save() creates backups before
atomic saves, preventing data loss from accidental deletions or corruption.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_when_file_exists(tmp_path) -> None:
    """Test that save() creates a .bak backup when previous file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    original_todos = [Todo(id=1, text="original data")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=1, text="new data")]
    storage.save(new_todos)

    # Verify backup file was created
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created"

    # Verify backup contains the original data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original data"

    # Verify main file has new data
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new data"


def test_save_rotates_backups_with_limit(tmp_path) -> None:
    """Test that backups rotate with a limit (default 3)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="v0")])

    # Perform multiple saves - should create rotating backups
    for i in range(1, 6):
        storage.save([Todo(id=1, text=f"v{i}")])

    # Default limit is 3, so we should have .bak, .bak.1, .bak.2
    backup_base = tmp_path / "todo.json.bak"
    backup_1 = tmp_path / "todo.json.bak.1"
    backup_2 = tmp_path / "todo.json.bak.2"

    assert backup_base.exists(), ".bak should exist"
    assert backup_1.exists(), ".bak.1 should exist"
    assert backup_2.exists(), ".bak.2 should exist"

    # .bak.3 should not exist (exceeds limit)
    backup_3 = tmp_path / "todo.json.bak.3"
    assert not backup_3.exists(), ".bak.3 should not exist (exceeds limit)"

    # Verify rotation order: .bak has v4, .bak.1 has v3, .bak.2 has v2
    # Each save rotates: existing .bak -> .bak.1, .bak.1 -> .bak.2, etc.
    # After 5 saves (v1-v5), the backups should contain v4, v3, v2 respectively
    content_bak = json.loads(backup_base.read_text(encoding="utf-8"))
    content_bak1 = json.loads(backup_1.read_text(encoding="utf-8"))
    content_bak2 = json.loads(backup_2.read_text(encoding="utf-8"))

    assert content_bak[0]["text"] == "v4"
    assert content_bak1[0]["text"] == "v3"
    assert content_bak2[0]["text"] == "v2"


def test_backup_deleted_when_limit_exceeded(tmp_path) -> None:
    """Test that oldest backup is deleted when limit is exceeded."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="v0")])

    # Create more backups than limit (3)
    for i in range(1, 5):
        storage.save([Todo(id=1, text=f"v{i}")])

    # Only 3 backups should exist (limit)
    backup_files = list(tmp_path.glob("todo.json.bak*"))
    assert len(backup_files) == 3, f"Expected 3 backups, found {len(backup_files)}"

    # Oldest backup (v1) should have been deleted
    # Backups should be v3, v2, v1's original position got rotated out


def test_no_backup_created_on_first_save(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no previous file to backup
    storage.save([Todo(id=1, text="first save")])

    # No backup file should exist
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "No backup should be created on first save"


def test_backup_with_custom_limit(tmp_path) -> None:
    """Test that backup limit can be customized via TodoStorage parameter."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="v0")])

    # Create backups with custom limit of 2
    for i in range(1, 5):
        storage.save([Todo(id=1, text=f"v{i}")], backup_limit=2)

    # Only 2 backups should exist
    backup_files = list(tmp_path.glob("todo.json.bak*"))
    assert len(backup_files) == 2, f"Expected 2 backups with custom limit, found {len(backup_files)}"


def test_load_fallback_to_backup_when_corrupted(tmp_path) -> None:
    """Test that load() can fall back to backup when main file is corrupted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    original_todos = [Todo(id=1, text="backup data"), Todo(id=2, text="another")]
    storage.save(original_todos)

    # Save new data (creates backup)
    storage.save([Todo(id=1, text="new data")])

    # Corrupt the main file
    db.write_text("{invalid json content", encoding="utf-8")

    # load() with use_backup=True should fall back to backup
    loaded = storage.load(use_backup=True)
    assert len(loaded) == 2
    assert loaded[0].text == "backup data"
    assert loaded[1].text == "another"


def test_load_raises_without_fallback_when_corrupted(tmp_path) -> None:
    """Test that load() raises error when main file is corrupted and fallback not enabled."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save data
    storage.save([Todo(id=1, text="data")])
    storage.save([Todo(id=1, text="new")])  # Creates backup

    # Corrupt the main file
    db.write_text("{invalid json", encoding="utf-8")

    # load() without use_backup should raise error
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load(use_backup=False)


def test_load_returns_empty_when_no_file_or_backup(tmp_path) -> None:
    """Test that load() returns empty list when no file or backup exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No file exists
    loaded = storage.load(use_backup=True)
    assert loaded == []

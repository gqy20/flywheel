"""Regression tests for issue #2334: Automatic backup before overwrite on save.

Issue: The save() method overwrites the existing file without creating a backup,
which means users have no recovery path from accidental deletions, bad data, or bugs.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_on_overwrite(tmp_path) -> None:
    """Issue #2334: A backup file should be created when overwriting existing file.

    Before fix: No backup is created, original data is lost on overwrite
    After fix: .bak file should contain the original content before overwrite
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task"), Todo(id=2, text="to be backed up")]
    storage.save(original_todos)

    # Save new data (should trigger backup)
    new_todos = [Todo(id=1, text="new task")]
    storage.save(new_todos)

    # Verify backup was created
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created on overwrite"

    # Verify backup contains original data
    backup_storage = TodoStorage(str(backup_path))
    backup_todos = backup_storage.load()
    assert len(backup_todos) == 2
    assert backup_todos[0].text == "original task"
    assert backup_todos[1].text == "to be backed up"


def test_backup_rotation_keeps_only_n_recent(tmp_path) -> None:
    """Issue #2334: Backup rotation should keep only N most recent backups.

    Default backup count is 3. After 5 saves, only 3 backup files should exist.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initial save
    storage.save([Todo(id=1, text="version 0")])

    # Perform 5 more saves (should create backups)
    for i in range(1, 6):
        storage.save([Todo(id=1, text=f"version {i}")])

    # Check for backup files
    backup_files = sorted(tmp_path.glob("todo.json.bak*"))

    # Should have exactly 3 backups (default TODO_BACKUP_COUNT)
    assert len(backup_files) == 3, f"Expected 3 backup files, got {len(backup_files)}"

    # The most recent backup should have the latest "original" content
    # (which would be version 4 before version 5 was written)
    most_recent_backup = max(backup_files, key=lambda p: p.stat().st_mtime)
    backup_storage = TodoStorage(str(most_recent_backup))
    backup_todos = backup_storage.load()
    assert backup_todos[0].text == "version 4"


def test_backup_count_zero_disables_backups(tmp_path) -> None:
    """Issue #2334: TODO_BACKUP_COUNT=0 should disable backup creation."""
    db = tmp_path / "todo.json"

    with patch.dict(os.environ, {"TODO_BACKUP_COUNT": "0"}):
        storage = TodoStorage(str(db))

        # Create initial data
        storage.save([Todo(id=1, text="original")])

        # Save new data
        storage.save([Todo(id=1, text="new")])

    # Verify no backup was created
    backup_files = list(tmp_path.glob("todo.json.bak*"))
    assert len(backup_files) == 0, "No backup files should be created when TODO_BACKUP_COUNT=0"


def test_backup_failure_doesnt_prevent_main_save(tmp_path) -> None:
    """Issue #2334: Backup creation failure should not prevent the main save operation.

    Even if backup fails for some reason, the main save should still succeed.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    storage.save([Todo(id=1, text="original")])

    # Mock os.replace to fail for backup files but succeed for main file
    original_replace = os.replace
    call_count = {"count": 0}

    def selective_replace(src, dst):
        call_count["count"] += 1
        # If this looks like a backup operation, let it fail
        if ".bak" in str(dst):
            raise OSError("Simulated backup failure")
        # Otherwise use original
        return original_replace(src, dst)

    with patch("flywheel.storage.os.replace", side_effect=selective_replace):
        # Save should still succeed even if backup fails
        storage.save([Todo(id=1, text="new")])

    # Verify main file was updated
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new"


def test_first_save_creates_no_backup(tmp_path) -> None:
    """Issue #2334: No backup should be created on first save (no existing file).

    Backups are only meaningful when overwriting existing data.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save (no existing file)
    storage.save([Todo(id=1, text="first todo")])

    # Verify no backup was created
    backup_files = list(tmp_path.glob("todo.json.bak*"))
    assert len(backup_files) == 0, "No backup should be created on first save"


def test_custom_backup_count_from_env(tmp_path) -> None:
    """Issue #2334: TODO_BACKUP_COUNT should be configurable via environment variable."""
    db = tmp_path / "todo.json"

    with patch.dict(os.environ, {"TODO_BACKUP_COUNT": "5"}):
        storage = TodoStorage(str(db))

        # Initial save
        storage.save([Todo(id=1, text="version 0")])

        # Perform 7 more saves
        for i in range(1, 8):
            storage.save([Todo(id=1, text=f"version {i}")])

    # Should have exactly 5 backups (from TODO_BACKUP_COUNT env var)
    backup_files = sorted(tmp_path.glob("todo.json.bak*"))
    assert len(backup_files) == 5, f"Expected 5 backup files, got {len(backup_files)}"


def test_backup_has_same_content_as_original(tmp_path) -> None:
    """Issue #2334: Backup should have exact same content as original before overwrite."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create original data with special characters
    original_todos = [
        Todo(id=1, text="task with unicode: 你好"),
        Todo(id=2, text='task with "quotes"'),
        Todo(id=3, text="multiline\ncontent", done=True),
    ]
    storage.save(original_todos)

    # Get the original file content
    original_content = db.read_text(encoding="utf-8")

    # Save new data
    storage.save([Todo(id=1, text="new")])

    # Verify backup has identical content to original
    backup_path = tmp_path / "todo.json.bak"
    backup_content = backup_path.read_text(encoding="utf-8")

    assert backup_content == original_content, "Backup should match original content exactly"


def test_backup_respects_atomic_write_pattern(tmp_path) -> None:
    """Issue #2334: Backup creation should respect atomic write pattern.

    The backup should be created atomically to prevent partial backups.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create original data
    original_todos = [Todo(id=1, text="original data that should be backed up")]
    storage.save(original_todos)

    # Save new data
    new_todos = [Todo(id=1, text="new data")]
    storage.save(new_todos)

    # Verify backup exists and is valid JSON
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup should exist"

    # Should be able to load from backup without errors
    backup_storage = TodoStorage(str(backup_path))
    backup_todos = backup_storage.load()

    assert len(backup_todos) == 1
    assert backup_todos[0].text == "original data that should be backed up"

    # Verify main file has new data
    main_todos = storage.load()
    assert len(main_todos) == 1
    assert main_todos[0].text == "new data"

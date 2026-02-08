"""Regression tests for issue #2334: Add automatic backup before overwrite on save.

Issue: os.replace in save() overwrites without backup, leaving no recovery path
from accidental deletions, bad data, or bugs.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_file_created_on_overwrite(tmp_path, monkeypatch) -> None:
    """Issue #2334: A .bak backup should be created when overwriting existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file with some content
    original_todos = [Todo(id=1, text="original data")]
    storage.save(original_todos)
    original_content = db.read_text(encoding="utf-8")

    # Overwrite with new content - should create backup
    new_todos = [Todo(id=2, text="new data")]
    storage.save(new_todos)

    # Backup file should exist
    backup_path = db.parent / f"{db.name}.bak"
    assert backup_path.exists(), "Backup file should be created on overwrite"

    # Backup should contain original content
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == original_content, "Backup should have original content"


def test_backup_not_created_on_first_save(tmp_path) -> None:
    """Issue #2334: No backup should be created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no file exists yet
    todos = [Todo(id=1, text="first save")]
    storage.save(todos)

    # Backup file should NOT exist
    backup_path = db.parent / f"{db.name}.bak"
    assert not backup_path.exists(), "No backup on first save"


def test_backup_rotation_keeps_only_n_backups(tmp_path, monkeypatch) -> None:
    """Issue #2334: Backup rotation should keep only N most recent backups."""
    # Set backup count to 3
    monkeypatch.setenv("TODO_BACKUP_COUNT", "3")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create multiple saves to generate backups
    for i in range(5):
        todos = [Todo(id=i, text=f"save {i}")]
        storage.save(todos)

    # Check that we have exactly N backup files
    backup_files = sorted(db.parent.glob(f"{db.name}.bak*"))
    assert len(backup_files) == 3, f"Should keep only 3 backups, found {len(backup_files)}"

    # The oldest backup should be from save 2 (saves 0, 1 were rotated out)
    # Most recent backup should be from save 4
    for backup in backup_files:
        data = json.loads(backup.read_text(encoding="utf-8"))
        assert isinstance(data, list)


def test_backup_count_zero_disables_backups(tmp_path, monkeypatch) -> None:
    """Issue #2334: TODO_BACKUP_COUNT=0 should disable backups."""
    monkeypatch.setenv("TODO_BACKUP_COUNT", "0")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])

    # Second save - would normally create backup
    storage.save([Todo(id=2, text="second")])

    # No backup files should exist
    backup_files = list(db.parent.glob(f"{db.name}.bak*"))
    assert len(backup_files) == 0, "No backups should be created when TODO_BACKUP_COUNT=0"


def test_backup_failure_doesnt_prevent_main_save(tmp_path) -> None:
    """Issue #2334: If backup creation fails, main save should still succeed."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="original")])

    # Mock shutil.copy to fail but allow the rest of save to proceed
    def failing_copy(src, dst, **kwargs):
        raise OSError("Simulated backup failure")

    with patch("flywheel.storage.shutil.copy", failing_copy):
        # This should NOT raise - backup failure is suppressed
        storage.save([Todo(id=2, text="new")])

    # Main file should still be updated with new content
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new"


def test_backup_uses_default_count_when_env_not_set(tmp_path, monkeypatch) -> None:
    """Issue #2334: Should use default backup count when env var is not set."""
    # Ensure env var is not set
    monkeypatch.delenv("TODO_BACKUP_COUNT", raising=False)

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create saves to generate backups
    for i in range(5):
        storage.save([Todo(id=i, text=f"save {i}")])

    # Should use default count (3)
    backup_files = sorted(db.parent.glob(f"{db.name}.bak*"))
    assert len(backup_files) == 3, f"Default should keep 3 backups, found {len(backup_files)}"


def test_backup_content_matches_pre_overwrite_state(tmp_path) -> None:
    """Issue #2334: Backup should contain exact content from before overwrite."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create complex original content
    original = [
        Todo(id=1, text="task 1", done=True),
        Todo(id=2, text="task with unicode: 你好"),
        Todo(id=3, text="task with \"quotes\"", done=False),
    ]
    storage.save(original)
    original_content = db.read_text(encoding="utf-8")

    # Overwrite with different content
    storage.save([Todo(id=99, text="completely different")])

    # Backup should match original exactly
    backup_path = db.parent / f"{db.name}.bak"
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == original_content

    # Verify backup contains valid todo data
    backup_data = json.loads(backup_content)
    assert len(backup_data) == 3
    assert backup_data[0]["text"] == "task 1"
    assert backup_data[1]["text"] == "task with unicode: 你好"

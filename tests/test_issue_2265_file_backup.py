"""Tests for file backup functionality in TodoStorage.save().

This test suite verifies that TodoStorage.save() creates backup files
before overwriting, preventing data loss and providing recovery options.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_file_when_enabled(tmp_path) -> None:
    """Test that save creates .backup file when enable_backups=True."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # Create initial file
    original_todos = [Todo(id=1, text="original data")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=2, text="new data")]
    storage.save(new_todos)

    # Verify backup file exists
    backup_path = db.with_suffix(db.suffix + ".backup")
    assert backup_path.exists(), "Backup file should be created when enabled"

    # Verify backup contains original data
    backup_storage = TodoStorage(str(backup_path))
    backup_todos = backup_storage.load()
    assert len(backup_todos) == 1
    assert backup_todos[0].text == "original data"


def test_backup_disabled_by_default(tmp_path) -> None:
    """Test that backups are NOT created by default (enable_backups=False)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))  # Default: enable_backups=False

    # Create initial file
    original_todos = [Todo(id=1, text="original data")]
    storage.save(original_todos)

    # Save new data
    new_todos = [Todo(id=2, text="new data")]
    storage.save(new_todos)

    # Verify NO backup file was created
    backup_path = db.with_suffix(db.suffix + ".backup")
    assert not backup_path.exists(), "Backup file should NOT be created when disabled"


def test_max_backups_limits_backup_count(tmp_path) -> None:
    """Test that max_backups=1 only keeps one backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True, max_backups=1)

    # First save - creates initial file
    storage.save([Todo(id=1, text="first")])

    # Second save - should create backup of "first"
    storage.save([Todo(id=2, text="second")])

    # Third save - should create backup of "second", replacing backup of "first"
    storage.save([Todo(id=3, text="third")])

    # Verify only one backup file exists
    backup_path = db.with_suffix(db.suffix + ".backup")
    assert backup_path.exists(), "Backup file should exist"

    # Verify backup contains "second" (the data before "third" was saved)
    backup_storage = TodoStorage(str(backup_path))
    backup_todos = backup_storage.load()
    assert len(backup_todos) == 1
    assert backup_todos[0].text == "second"


def test_backup_failure_does_not_affect_main_save(tmp_path) -> None:
    """Test that if backup creation fails, main save still succeeds."""
    db = tmp_path / "todo.json"
    # Use a directory path that will cause backup to fail
    # by creating a file where a directory would be needed
    storage = TodoStorage(str(db), enable_backups=True)

    # Create initial file
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Create a file that will block backup creation
    # (simulate backup failure by making backup path a directory)
    backup_path = db.with_suffix(db.suffix + ".backup")
    backup_path.mkdir()  # Create as directory to cause copy failure

    # Save should still succeed even though backup fails
    new_todos = [Todo(id=2, text="new")]
    storage.save(new_todos)  # Should not raise

    # Verify main file has new data
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new"


def test_multiple_backups_with_rotation(tmp_path) -> None:
    """Test backup rotation when max_backups > 1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True, max_backups=2)

    # Create initial file
    storage.save([Todo(id=1, text="first")])

    # First backup
    storage.save([Todo(id=2, text="second")])
    backup_1_path = db.with_suffix(db.suffix + ".backup.1")
    assert backup_1_path.exists()
    backup_1_storage = TodoStorage(str(backup_1_path))
    assert backup_1_storage.load()[0].text == "first"

    # Second backup - should rotate
    storage.save([Todo(id=3, text="third")])
    backup_2_path = db.with_suffix(db.suffix + ".backup.2")
    assert backup_2_path.exists()
    backup_2_storage = TodoStorage(str(backup_2_path))
    # .backup.2 contains "first" (rotated from .backup.1)
    assert backup_2_storage.load()[0].text == "first"

    # Third save - should rotate out oldest
    storage.save([Todo(id=4, text="fourth")])
    # .backup.1 should now contain "third" (most recent backup)
    backup_1_storage = TodoStorage(str(backup_1_path))
    assert backup_1_storage.load()[0].text == "third"
    # .backup.2 should now contain "second" (rotated from .backup.1)
    backup_2_storage = TodoStorage(str(backup_2_path))
    assert backup_2_storage.load()[0].text == "second"


def test_no_backup_on_first_save(tmp_path) -> None:
    """Test that no backup is created when target file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # First save - file doesn't exist yet, no backup should be created
    storage.save([Todo(id=1, text="first")])

    # Verify NO backup file was created
    backup_path = db.with_suffix(db.suffix + ".backup")
    assert not backup_path.exists(), "No backup should be created on first save"


def test_backup_preserves_file_content_exactly(tmp_path) -> None:
    """Test that backup preserves the exact content of the original file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # Create complex todos with special characters
    original_todos = [
        Todo(id=1, text='Task with "quotes"'),
        Todo(id=2, text="Task with unicode: 你好"),
        Todo(id=3, text="Task with \n newline"),
        Todo(id=4, text="Task with \\t tab", done=True),
    ]
    storage.save(original_todos)

    # Read original file content
    original_content = db.read_text(encoding="utf-8")

    # Save new data
    new_todos = [Todo(id=5, text="new task")]
    storage.save(new_todos)

    # Verify backup content matches original exactly
    backup_path = db.with_suffix(db.suffix + ".backup")
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == original_content, "Backup should preserve exact file content"

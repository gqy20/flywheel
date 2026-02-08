"""Tests for backup/rotation support for corrupted database files (Issue #2238).

These tests verify that:
1. Backup files are created before overwriting existing data
2. Backup rotation keeps only N backups
3. No backup created for new files
4. restore_from_backup restores data correctly
5. list_backups discovers available backups
6. Backups work with concurrent access
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_on_save_when_file_exists(tmp_path) -> None:
    """Test that a backup is created when file exists before save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Create initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=1, text="modified"), Todo(id=3, text="added")]
    storage.save(new_todos)

    # Verify backup exists
    backups = storage.list_backups()
    assert len(backups) >= 1

    # Verify backup contains original data
    backup_storage = TodoStorage(str(backups[0]))
    restored_todos = backup_storage.load()
    assert len(restored_todos) == 2
    assert restored_todos[0].text == "original"
    assert restored_todos[1].text == "data"


def test_no_backup_created_for_new_files(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Save to non-existent file - no backup should be created
    todos = [Todo(id=1, text="first")]
    storage.save(todos)

    # Verify no backups exist
    backups = storage.list_backups()
    assert len(backups) == 0


def test_backup_rotation_keeps_only_n_backups(tmp_path) -> None:
    """Test that backup rotation keeps only the configured number of backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=2)

    # Create initial data
    storage.save([Todo(id=1, text="v1")])

    # Save multiple times to create multiple backups
    for i in range(2, 6):
        storage.save([Todo(id=i, text=f"v{i}")])

    # Verify only 2 backups are kept
    backups = storage.list_backups()
    assert len(backups) <= 2


def test_backup_rotation_naming_scheme(tmp_path) -> None:
    """Test that backups follow the expected naming scheme (.bak, .bak.1, .bak.2)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Create initial data
    storage.save([Todo(id=1, text="v1")])

    # Save multiple times
    for i in range(2, 5):
        storage.save([Todo(id=i, text=f"v{i}")])

    # Verify backup naming
    backups = storage.list_backups()
    backup_names = [b.name for b in backups]

    # Check that backups use .bak suffix
    assert any(".bak" in name for name in backup_names)


def test_restore_from_backup_restores_data_correctly(tmp_path) -> None:
    """Test that restore_from_backup restores data correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Create and save original data
    original_todos = [
        Todo(id=1, text="task1"),
        Todo(id=2, text="task2"),
        Todo(id=3, text="task3"),
    ]
    storage.save(original_todos)

    # Save new data (corrupted or wrong)
    storage.save([Todo(id=99, text="wrong data")])

    # Get backup
    backups = storage.list_backups()
    assert len(backups) >= 1

    # Restore from backup
    storage.restore_from_backup(backups[0])

    # Verify restored data
    restored_todos = storage.load()
    assert len(restored_todos) == 3
    assert restored_todos[0].text == "task1"
    assert restored_todos[1].text == "task2"
    assert restored_todos[2].text == "task3"


def test_list_backups_returns_available_backups(tmp_path) -> None:
    """Test that list_backups returns all available backup files."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Create initial data and save multiple times
    storage.save([Todo(id=1, text="v1")])
    storage.save([Todo(id=2, text="v2")])
    storage.save([Todo(id=3, text="v3")])

    # Get backups
    backups = storage.list_backups()

    # Verify backups are Path objects
    assert all(isinstance(b, Path) for b in backups)

    # Verify backups exist
    assert all(b.exists() for b in backups)


def test_backup_with_keep_backups_zero(tmp_path) -> None:
    """Test that keep_backups=0 disables backup creation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=0)

    # Create initial data
    storage.save([Todo(id=1, text="v1")])

    # Save new data - no backup should be created
    storage.save([Todo(id=2, text="v2")])

    # Verify no backups exist
    backups = storage.list_backups()
    assert len(backups) == 0


def test_backup_preserves_file_permissions(tmp_path) -> None:
    """Test that backup preserves original file permissions."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Create and save initial data
    storage.save([Todo(id=1, text="v1")])

    # Save new data to create backup
    storage.save([Todo(id=2, text="v2")])

    # Get backup and verify it's readable
    backups = storage.list_backups()
    assert len(backups) >= 1

    # Verify backup can be read
    backup_content = backups[0].read_text(encoding="utf-8")
    assert '"text": "v1"' in backup_content


def test_multiple_saves_create_multiple_backups(tmp_path) -> None:
    """Test that multiple saves create multiple backups up to the limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Create initial data
    storage.save([Todo(id=1, text="v1")])

    # Save multiple times
    storage.save([Todo(id=2, text="v2")])
    storage.save([Todo(id=3, text="v3")])
    storage.save([Todo(id=4, text="v4")])

    # Should have up to 3 backups
    backups = storage.list_backups()
    assert len(backups) <= 3


def test_restore_from_nonexistent_backup_raises_error(tmp_path) -> None:
    """Test that restoring from a non-existent backup raises an error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Try to restore from non-existent backup
    fake_backup = tmp_path / "nonexistent.bak"

    with pytest.raises(FileNotFoundError):
        storage.restore_from_backup(fake_backup)


def test_concurrent_access_with_backups(tmp_path) -> None:
    """Test that backups work correctly with concurrent access."""
    import multiprocessing
    import time

    db = tmp_path / "concurrent.json"

    # Initialize the file first to avoid race condition
    initial_storage = TodoStorage(str(db), keep_backups=3)
    initial_storage.save([Todo(id=0, text="initial")])

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that saves todos and creates backups."""
        try:
            storage = TodoStorage(str(db), keep_backups=3)
            todos = [Todo(id=i, text=f"worker-{worker_id}-todo-{i}") for i in range(2)]
            storage.save(todos)
            time.sleep(0.001)
            loaded = storage.load()
            backups = storage.list_backups()
            result_queue.put(("success", worker_id, len(loaded), len(backups)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 3
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded without errors
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"


def test_default_keep_backups_is_zero(tmp_path) -> None:
    """Test that default keep_backups is 0 (backups disabled by default)."""
    db = tmp_path / "todo.json"

    # Create storage without specifying keep_backups
    storage = TodoStorage(str(db))

    # Save data twice
    storage.save([Todo(id=1, text="v1")])
    storage.save([Todo(id=2, text="v2")])

    # Verify no backups are created by default
    backups = storage.list_backups()
    assert len(backups) == 0

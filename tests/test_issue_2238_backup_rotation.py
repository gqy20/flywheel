"""Tests for database backup/rotation support (Issue #2238).

These tests verify that:
1. Backups are created when file exists before save
2. Backup rotation keeps only N backups
3. No backup created for new files
4. restore_from_backup restores data correctly
5. Backups work with concurrent access
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_when_file_exists(tmp_path) -> None:
    """Test that backup is created when file exists before save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Create initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=1, text="updated"), Todo(id=3, text="new")]
    storage.save(new_todos)

    # Verify backup file exists
    backups = storage.list_backups()
    assert len(backups) >= 1, "At least one backup should be created"

    # Verify backup contains original data
    backup_storage = TodoStorage(str(backups[0]))
    backup_data = backup_storage.load()
    assert len(backup_data) == 2
    assert backup_data[0].text == "original"
    assert backup_data[1].text == "data"


def test_backup_rotation_keeps_only_n_backups(tmp_path) -> None:
    """Test that backup rotation keeps only N backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Create initial data
    storage.save([Todo(id=1, text="v1")])

    # Perform multiple saves to create multiple backups
    for i in range(2, 6):  # Create 5 versions total
        storage.save([Todo(id=1, text=f"v{i}")])

    # Should only keep 3 backups
    backups = storage.list_backups()
    assert len(backups) == 3, f"Should keep only 3 backups, got {len(backups)}"


def test_no_backup_for_new_files(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Save to new file - no backup should be created
    storage.save([Todo(id=1, text="first")])

    backups = storage.list_backups()
    assert len(backups) == 0, "No backup should be created for new files"


def test_restore_from_backup_restores_data(tmp_path) -> None:
    """Test that restore_from_backup restores data correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Create original data
    original_todos = [Todo(id=1, text="backup1"), Todo(id=2, text="backup2")]
    storage.save(original_todos)

    # Overwrite with new data
    storage.save([Todo(id=1, text="current")])

    # Get backup path
    backups = storage.list_backups()
    assert len(backups) >= 1

    # Restore from backup
    storage.restore_from_backup(backups[0])

    # Verify restored data matches original
    restored = storage.load()
    assert len(restored) == 2
    assert restored[0].text == "backup1"
    assert restored[1].text == "backup2"


def test_list_backups_returns_sorted_paths(tmp_path) -> None:
    """Test that list_backups returns backup paths sorted by modification time (newest first)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=5)

    # Create multiple versions
    for i in range(1, 5):  # v1, v2, v3, v4
        storage.save([Todo(id=1, text=f"version{i}")])

    backups = storage.list_backups()
    # First save (v1) creates no backup, then v2 creates .bak, v3 creates .bak (v2) + .bak.1 (v1), etc.
    # After 4 saves: .bak (v3), .bak.1 (v2), .bak.2 (v1) = 3 backups
    assert len(backups) == 3

    # Backups should be sorted newest first
    # Load each backup to verify content
    backup_contents = []
    for backup_path in backups:
        backup_storage = TodoStorage(str(backup_path))
        data = backup_storage.load()
        backup_contents.append(data[0].text)

    # Newest backup (.bak) should have version3 (last saved before version4)
    assert backup_contents[0] == "version3"
    assert backup_contents[1] == "version2"
    assert backup_contents[2] == "version1"


def test_default_keep_backups_is_three(tmp_path) -> None:
    """Test that default keep_backups parameter is 3."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    assert storage.keep_backups == 3, "Default keep_backups should be 3"


def test_backup_with_zero_keeps_no_backups(tmp_path) -> None:
    """Test that keep_backups=0 disables backup creation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=0)

    # Create initial data
    storage.save([Todo(id=1, text="v1")])

    # Save again - no backup should be created
    storage.save([Todo(id=1, text="v2")])

    backups = storage.list_backups()
    assert len(backups) == 0, "No backups should be created when keep_backups=0"


def test_backup_naming_convention(tmp_path) -> None:
    """Test that backups follow the naming convention .bak, .bak.1, .bak.2, etc."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), keep_backups=3)

    # Create multiple versions
    for i in range(1, 4):
        storage.save([Todo(id=1, text=f"v{i}")])

    backups = storage.list_backups()
    backup_names = [b.name for b in backups]

    # Check for proper naming patterns
    assert any(b.endswith(".bak") or ".bak." in b for b in backup_names), \
        "Backups should use .bak or .bak.N naming convention"


def test_concurrent_backup_operations(tmp_path) -> None:
    """Test that backup operations work correctly with concurrent access."""
    import multiprocessing
    import time

    db = tmp_path / "concurrent_backup.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that saves todos multiple times."""
        try:
            storage = TodoStorage(str(db), keep_backups=3)
            for i in range(3):
                todos = [Todo(id=i, text=f"worker-{worker_id}-v{i}")]
                storage.save(todos)
                time.sleep(0.001)  # Small delay to increase race likelihood

            # Verify we can read back valid data
            loaded = storage.load()
            result_queue.put(("success", worker_id, len(loaded)))
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

    # Verify final state is valid
    storage = TodoStorage(str(db), keep_backups=3)
    final_todos = storage.load()
    assert isinstance(final_todos, list)

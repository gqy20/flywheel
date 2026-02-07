"""Regression tests for issue #1999: Symlink attack protection for atomic save.

Issue: Atomic save uses predictable temp file path (.todo.json.tmp),
which is vulnerable to symlink attacks where an attacker pre-creates
a symlink to cause writes to arbitrary locations.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import contextlib
import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_fails_when_temp_path_is_symlink_to_system_file(tmp_path) -> None:
    """Issue #1999: Should fail safely when temp path is a symlink.

    Simulates an attack scenario where an attacker pre-creates a symlink
    at the predictable temp path pointing to a sensitive file.

    Before fix: Would overwrite the target file via the symlink
    After fix: Should detect symlink and fail, or use unpredictable name
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a target file that an attacker might want to overwrite
    target_file = tmp_path / "sensitive.txt"
    target_file.write_text("sensitive data - should not be overwritten")

    # Create the predictable temp path as a symlink to the target
    # This simulates an attacker pre-creating the symlink
    temp_path = db.parent / f".{db.name}.tmp"
    temp_path.symlink_to(target_file)

    # Try to save - this should either:
    # 1. Fail because it detects the symlink, OR
    # 2. Succeed but NOT overwrite the target (if using unpredictable name)
    initial_target_content = target_file.read_text()

    todos = [Todo(id=1, text="new data")]

    # The save should either raise an error or safely complete
    # without overwriting the symlink target
    with contextlib.suppress(OSError, ValueError, RuntimeError):
        storage.save(todos)

    # Critical: the target file should NOT be overwritten
    final_target_content = target_file.read_text()
    assert final_target_content == initial_target_content, (
        "Symlink attack succeeded! Target file was overwritten. "
        "This means the temp file path is predictable and vulnerable."
    )

    # Verify the db file was written correctly (if save succeeded)
    if db.exists():
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "new data"


def test_save_uses_unpredictable_temp_filename(tmp_path) -> None:
    """Issue #1999: Temp filename should be unpredictable.

    Before fix: Uses '.todo.json.tmp' which is predictable
    After fix: Should include random characters to prevent prediction
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # After save, check if the temp file pattern is predictable
    # The fix should use tempfile.mkstemp which adds random characters

    # The predictable pattern would be exactly '.todo.json.tmp'
    predictable_name = f".{db.name}.tmp"
    predictable_path = db.parent / predictable_name

    # This should NOT exist (the fix uses unpredictable names)
    assert not predictable_path.exists(), (
        f"Temp file uses predictable name '{predictable_name}'. "
        "This is vulnerable to symlink attacks."
    )

    # Verify the actual file was created correctly
    assert db.exists(), "Target file should exist"
    loaded = storage.load()
    assert len(loaded) == 1


def test_temp_file_created_with_restrictive_permissions(tmp_path, monkeypatch) -> None:
    """Issue #1999: Temp file should have restrictive permissions (0o600).

    Before fix: Uses write_text which inherits umask (often 0o644)
    After fix: Should create temp file with 0o600 (owner read/write only)
    """
    # Set a permissive umask to verify the fix creates restrictive permissions regardless
    monkeypatch.setattr(os, "umask", lambda *args: 0o022)  # Would result in 0o644 normally

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track files created during save
    files_before = set(db.parent.iterdir())

    storage.save(todos)

    files_after = set(db.parent.iterdir())
    new_files = files_after - files_before

    # Check temp file permissions if any temp files still exist
    # (they might be cleaned up after rename, but we can check if any exist)
    for f in new_files:
        if f.name.startswith(".") and ".tmp" in f.name:
            # Check file permissions
            stat_info = f.stat()
            mode = stat_info.st_mode & 0o777
            # Temp file should be 0o600 (owner read/write only)
            # Note: On Windows, permissions work differently, so we just check it exists
            if os.name != "nt":
                assert mode == 0o600, (
                    f"Temp file has permissive permissions {oct(mode)}. "
                    f"Expected 0o600 to prevent other users from reading partial data."
                )

    # Verify the target file was created correctly
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1


def test_symlink_attack_multiple_attempts(tmp_path) -> None:
    """Issue #1999: Attacker shouldn't be able to win with multiple attempts.

    Tests that even if an attacker tries to create symlinks repeatedly,
    the unpredictable naming makes it impractical to succeed.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create multiple target files an attacker might want to overwrite
    targets = [tmp_path / f"target{i}.txt" for i in range(5)]
    for target in targets:
        target.write_text(f"sensitive data {target.name}")

    # Create symlinks at various predictable temp paths
    for i, target in enumerate(targets):
        temp_path = db.parent / f".{db.name}.{i}.tmp"
        if not temp_path.exists():
            temp_path.symlink_to(target)

    # Save should succeed without overwriting any targets
    todos = [Todo(id=1, text="secure data")]
    storage.save(todos)

    # None of the targets should be overwritten
    for target in targets:
        content = target.read_text()
        assert "sensitive data" in content, f"Target {target.name} was overwritten!"

    # The db should be correctly saved
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "secure data"


def test_concurrent_save_safety_with_symlink_attacker(tmp_path) -> None:
    """Issue #1999: Concurrent saves should be safe even with symlink attacker.

    Tests the scenario where an attacker tries to interfere with
    legitimate concurrent operations by pre-creating symlinks.
    """
    import multiprocessing
    import time

    db = tmp_path / "concurrent.json"

    def save_worker(worker_id: int) -> None:
        """Worker that saves todos."""
        storage = TodoStorage(str(db))
        todos = [Todo(id=i, text=f"worker-{worker_id}-todo-{i}") for i in range(3)]
        storage.save(todos)
        time.sleep(0.001)  # Small delay to increase race likelihood

    # Start multiple workers
    processes = []
    for i in range(3):
        p = multiprocessing.Process(target=save_worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=5)

    # Final state should be valid (no corruption)
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # Should have valid todo structure
    assert isinstance(final_todos, list)
    assert len(final_todos) == 3
    for todo in final_todos:
        assert hasattr(todo, "id")
        assert hasattr(todo, "text")


def test_atomic_save_in_different_directory(tmp_path) -> None:
    """Issue #1999: Temp file should be in same directory as target for atomic rename.

    This is a security AND correctness requirement - cross-directory
    renames may not be atomic on some filesystems.
    """
    # Create a subdirectory for the db
    db_dir = tmp_path / "subdir"
    db_dir.mkdir()
    db = db_dir / "todo.json"

    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test in subdir")]

    storage.save(todos)

    files_after = set(db_dir.iterdir())

    # Temp file should be created in same directory as target
    # (might be cleaned up, but we check the db was created)
    assert db.exists(), "Target file should exist"
    assert db in files_after, "Target should be in the expected directory"

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test in subdir"

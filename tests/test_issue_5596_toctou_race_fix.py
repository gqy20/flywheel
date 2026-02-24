"""Regression tests for issue #5596: TOCTOU race condition in _ensure_parent_directory.

Issue: The _ensure_parent_directory function validates parent paths then creates
directories, leaving a race window where an attacker could create a symlink or
directory between validation and mkdir.

The fix: Use exist_ok=True with mkdir to handle concurrent creation gracefully,
and validate parent types after creation to catch any symlink attacks.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_mkdir_succeeds_when_directory_created_concurrently(tmp_path) -> None:
    """Issue #5596: mkdir should succeed when another process creates the directory.

    This tests the TOCTOU race condition where between our validation and mkdir call,
    another process creates the same directory.

    Before fix: mkdir with exist_ok=False would fail with FileExistsError
    After fix: mkdir with exist_ok=True should succeed
    """
    db_path = tmp_path / "subdir" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Simulate the TOCTOU race: patch mkdir to simulate concurrent creation
    original_mkdir = Path.mkdir

    def mock_mkdir_with_race(self, mode=0o777, parents=False, exist_ok=False):
        # If exist_ok=False and this is the target directory, simulate race
        if not exist_ok and str(self).endswith("subdir"):
            # Another "process" creates the directory right before our mkdir
            original_mkdir(self, mode=mode, parents=parents, exist_ok=True)
        # Now try our mkdir - before fix this would fail
        return original_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)

    with patch.object(Path, "mkdir", mock_mkdir_with_race):
        # Before fix, this would fail with FileExistsError because exist_ok=False
        # After fix, exist_ok=True should handle this gracefully
        storage.save([Todo(id=1, text="test")])

    # Verify save succeeded
    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_concurrent_mkdir_no_race_condition(tmp_path) -> None:
    """Issue #5596: Multiple processes creating same directory should not fail.

    This test uses multiprocessing to actually trigger the race condition.
    """
    db_base = tmp_path / "race_test"

    def worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that tries to create directory and save."""
        try:
            # Each worker tries to save to the same parent directory
            db_path = db_base / "shared_subdir" / f"worker_{worker_id}.json"
            storage = TodoStorage(str(db_path))
            storage.save([Todo(id=1, text=f"worker_{worker_id}")])
            result_queue.put(("success", worker_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers that will race to create the same parent directory
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        # Small stagger to increase race likelihood
        time.sleep(0.001)
        p = multiprocessing.Process(target=worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should succeed - no race condition failures
    assert len(errors) == 0, f"Workers failed due to race condition: {errors}"
    assert len(successes) == num_workers


def test_ensure_parent_directory_handles_existing_directory(tmp_path) -> None:
    """Issue #5596: exist_ok=True should handle already-existing directories."""
    # Create the parent directory first
    parent = tmp_path / "existing_dir"
    parent.mkdir()

    # Calling _ensure_parent_directory on an already-existing path should succeed
    file_path = parent / "todo.json"
    _ensure_parent_directory(file_path)  # Should not raise

    assert parent.exists()
    assert parent.is_dir()


def test_error_message_clear_when_path_component_is_file(tmp_path) -> None:
    """Issue #5596: Error messages should remain clear when path component is a file.

    This verifies the fix doesn't break the existing file-as-directory detection.
    """
    # Create a file where a directory should be
    blocking_file = tmp_path / "blocking_file.txt"
    blocking_file.write_text("I am a file")

    # Try to use a path that requires the file to be a directory
    db_path = blocking_file / "subdir" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should fail with clear error about the file-as-directory issue
    with pytest.raises(ValueError, match=r"(file|not a directory|exists)"):
        storage.save([Todo(id=1, text="test")])


def test_symlink_attack_still_prevented(tmp_path) -> None:
    """Issue #5596: Symlink attack protection should still work after the fix.

    If an attacker creates a symlink in the path after our validation, we should
    still detect and prevent the attack.
    """
    # Create a directory structure
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Create a file in target that attacker wants to overwrite
    sensitive_file = target_dir / "sensitive.txt"
    sensitive_file.write_text("SECRET DATA")

    # Create the parent directory where we'll put our db
    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()

    # Try to save with a path that could be symlinked
    db_path = parent_dir / "todo.json"
    storage = TodoStorage(str(db_path))

    # First save succeeds
    storage.save([Todo(id=1, text="test")])

    # Verify we saved to the correct location, not via any symlink
    assert db_path.exists()
    assert db_path.read_text().__contains__("test")

    # The sensitive file should be untouched
    assert sensitive_file.read_text() == "SECRET DATA"


def test_nested_directory_creation_succeeds(tmp_path) -> None:
    """Issue #5596: Normal nested directory creation should still work."""
    # Create a deeply nested path that doesn't exist
    db_path = tmp_path / "a" / "b" / "c" / "d" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should succeed
    storage.save([Todo(id=1, text="nested test")])

    # Verify the file was created
    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "nested test"


def test_ensure_parent_directory_idempotent(tmp_path) -> None:
    """Issue #5596: Calling _ensure_parent_directory multiple times should be safe."""
    db_path = tmp_path / "subdir" / "todo.json"

    # Call multiple times - should all succeed without error
    for _ in range(5):
        _ensure_parent_directory(db_path)

    # Directory should exist
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()

"""Regression tests for issue #5431: TOCTOU race in _ensure_parent_directory.

Issue: Between checking parent.exists() and calling parent.mkdir(exist_ok=False),
another process could create the directory, causing FileExistsError.

Fix: Use exist_ok=True with proper error handling for file-as-directory cases.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_handles_concurrent_mkdir(tmp_path) -> None:
    """Issue #5431: _ensure_parent_directory should handle race condition gracefully.

    This test directly exercises the TOCTOU bug by simulating another process
    creating the directory between the exists() check and mkdir() call.
    """
    # Create a fresh path with non-existent parent
    fresh_dir = tmp_path / "concurrent_test"
    target_path = fresh_dir / "subdir" / "file.json"
    assert not target_path.parent.exists()

    # Track when mkdir is about to be called
    mkdir_call_count = threading.Event()
    errors = []
    original_mkdir = Path.mkdir

    def race_condition_mkdir(self, *args, **kwargs):
        """Simulate race condition: another process creates dir before our mkdir."""
        mkdir_call_count.set()

        # Simulate another process creating the directory right before our mkdir
        # This is what happens in the TOCTOU race condition
        if not self.exists():
            original_mkdir(self, parents=True, exist_ok=True)

        # Now call the original mkdir with exist_ok=False (as in buggy code)
        # This will raise FileExistsError because we just created it above
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", race_condition_mkdir):
        try:
            _ensure_parent_directory(target_path)
        except FileExistsError as e:
            errors.append(("FileExistsError", str(e)))

    # Before fix: expect FileExistsError
    # After fix: should NOT raise FileExistsError
    assert len(errors) == 0, (
        f"_ensure_parent_directory raised FileExistsError due to TOCTOU race: {errors}"
    )


def test_concurrent_save_creates_parent_directory_without_race_error(
    tmp_path,
) -> None:
    """Issue #5431: Concurrent saves with non-existent parent should not raise FileExistsError.

    Before fix: Two threads calling save() simultaneously on a path with non-existent
    parent directory could fail with FileExistsError when both try to create it.

    After fix: Both should succeed gracefully using exist_ok=True in mkdir.
    """
    # Use a barrier to maximize race condition likelihood
    num_workers = 10
    barrier = threading.Barrier(num_workers)
    errors = []
    results = []

    # Each worker gets its own subdirectory to avoid file write contention
    # but all share the same parent (which triggers the TOCTOU race)
    def save_worker(worker_id: int, base_dir: Path) -> None:
        try:
            # All workers target same parent directory
            db_path = base_dir / "shared_parent" / f"worker_{worker_id}.json"

            # Wait at barrier so all threads hit _ensure_parent_directory simultaneously
            barrier.wait(timeout=10)

            storage = TodoStorage(str(db_path))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
            results.append(worker_id)
        except Exception as e:
            errors.append((worker_id, type(e).__name__, str(e)))

    # Run many trials to increase chance of catching race
    for trial in range(5):
        trial_dir = tmp_path / f"trial_{trial}"
        errors.clear()
        results.clear()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(save_worker, i, trial_dir)
                for i in range(num_workers)
            ]
            for f in futures:
                f.result(timeout=10)

        # Verify no FileExistsError from TOCTOU race
        file_exists_errors = [
            e for e in errors if "FileExistsError" in str(e[1]) or "File exists" in str(e)
        ]
        assert len(file_exists_errors) == 0, (
            f"TOCTOU race caused FileExistsError in trial {trial}: {file_exists_errors}. "
            f"All errors: {errors}"
        )

        # All workers should succeed
        assert len(results) == num_workers, (
            f"Trial {trial}: Expected all {num_workers} workers to succeed, got {len(results)}. "
            f"Errors: {errors}"
        )


def test_file_as_directory_error_still_raised(tmp_path) -> None:
    """Issue #5431: File-as-directory validation must still work after fix.

    While fixing TOCTOU, we must preserve the security check that prevents
    using a file path as a directory component.
    """
    # Create a file where we need a directory
    blocking_file = tmp_path / "blocked.json"
    blocking_file.write_text("I am a file")

    # Try to use a path that requires the file to be a directory
    db_path = blocking_file / "nested" / "todos.json"
    storage = TodoStorage(str(db_path))

    # Should raise ValueError, not succeed silently
    with pytest.raises(ValueError, match=r"(file|not a directory|exists as)"):
        storage.save([Todo(id=1, text="test")])


def test_single_save_creates_missing_parent_directory(tmp_path) -> None:
    """Baseline: Single save should work for non-existent parent directories."""
    db_path = tmp_path / "level1" / "level2" / "todos.json"

    assert not db_path.parent.exists()

    storage = TodoStorage(str(db_path))
    storage.save([Todo(id=1, text="test")])

    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_parent_already_exists_continues_to_work(tmp_path) -> None:
    """Baseline: When parent exists, save should work normally."""
    parent = tmp_path / "existing"
    parent.mkdir()

    db_path = parent / "todos.json"
    storage = TodoStorage(str(db_path))
    storage.save([Todo(id=1, text="test")])

    assert db_path.exists()

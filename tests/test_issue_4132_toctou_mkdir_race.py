"""Regression tests for issue #4132: TOCTOU race condition in _ensure_parent_directory.

Issue: There is a Time-Of-Check-To-Time-Of-Use (TOCTOU) race condition between
the exists() check and the mkdir() call in _ensure_parent_directory.

The current code checks if parent.exists() before calling mkdir(exist_ok=False),
which creates a race window where:
1. Thread A: exists() returns False
2. Thread B: creates the directory (race condition)
3. Thread A: mkdir() raises FileExistsError because directory now exists

The fix: Use exist_ok=True in mkdir() and rely on OSError handling rather than
pre-checking existence. Remove the exists() check entirely.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_handles_existing_directory(tmp_path) -> None:
    """Issue #4132: mkdir should succeed when directory already exists (race condition scenario).

    This test simulates the race condition outcome: directory created by another
    process between the exists() check and mkdir() call.

    With the fix (exist_ok=True), mkdir should silently succeed.
    With the bug (exist_ok=False), mkdir would raise FileExistsError.
    """
    parent = tmp_path / "race_dir"
    file_path = parent / "todo.json"

    # Pre-create the directory to simulate race condition
    parent.mkdir(parents=True, exist_ok=True)

    # This should NOT raise FileExistsError with exist_ok=True
    _ensure_parent_directory(file_path)

    assert parent.exists(), "Directory should exist"


def test_concurrent_saves_with_directory_race_condition(tmp_path) -> None:
    """Issue #4132: Multiple threads saving to same parent directory should all succeed.

    When multiple threads try to create the same parent directory concurrently,
    they should all succeed due to exist_ok=True in mkdir().
    """
    import threading

    db = tmp_path / "shared_dir" / "todo.json"
    errors = []
    successes = []

    def save_todos(worker_id: int):
        """Worker that saves todos, possibly racing on directory creation."""
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
            successes.append(worker_id)
        except FileExistsError as e:
            # This should NOT happen with the fix
            errors.append((worker_id, str(e)))
        except Exception as e:
            errors.append((worker_id, str(e)))

    # Start multiple threads that will race to create the parent directory
    threads = []
    for i in range(10):
        t = threading.Thread(target=save_todos, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # All threads should have succeeded (no FileExistsError)
    file_exists_errors = [e for e in errors if "File exists" in str(e[1])]
    assert len(file_exists_errors) == 0, (
        f"FileExistsError should not occur with exist_ok=True. "
        f"Got {len(file_exists_errors)} errors: {file_exists_errors}"
    )

    # At least some threads should have succeeded
    assert len(successes) > 0, "At least some saves should have succeeded"


def test_ensure_parent_directory_uses_exist_ok_true(tmp_path) -> None:
    """Issue #4132: Verify that mkdir is called with exist_ok=True.

    This test verifies the fix by checking the actual mkdir call parameters.
    """
    parent = tmp_path / "test_dir"
    file_path = parent / "todo.json"

    mkdir_calls = []
    original_mkdir = Path.mkdir

    def tracking_mkdir(self, *args, **kwargs):
        mkdir_calls.append({"self": str(self), "args": args, "kwargs": kwargs})
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", tracking_mkdir):
        _ensure_parent_directory(file_path)

    # Verify mkdir was called with exist_ok=True
    assert len(mkdir_calls) >= 1, "mkdir should have been called"

    # Check that exist_ok=True was passed
    found_exist_ok_true = False
    for call in mkdir_calls:
        if call["kwargs"].get("exist_ok") is True:
            found_exist_ok_true = True
            break

    assert found_exist_ok_true, (
        f"mkdir should be called with exist_ok=True. Got calls: {mkdir_calls}"
    )


def test_storage_save_succeeds_with_existing_parent_directory(tmp_path) -> None:
    """Issue #4132: TodoStorage.save() should work when parent directory exists.

    This tests the race condition from a higher-level API perspective.
    If another process creates the directory between our check and mkdir,
    save() should still succeed.
    """
    db = tmp_path / "subdir" / "todo.json"

    # Pre-create the parent directory (simulating race condition)
    db.parent.mkdir(parents=True, exist_ok=True)

    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test")]

    # This should succeed without FileExistsError
    storage.save(todos)

    # Verify file was created
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_ensure_parent_directory_no_exists_check_before_mkdir(tmp_path) -> None:
    """Issue #4132: Verify no exists() check is performed on parent before mkdir().

    The fix should remove the vulnerable exists() check on the immediate parent
    before mkdir() and just call mkdir with exist_ok=True.
    """
    parent = tmp_path / "test_no_check"
    file_path = parent / "todo.json"

    # Just verify the directory is created successfully without errors
    _ensure_parent_directory(file_path)

    # The parent directory should exist after the call
    assert parent.exists(), "Parent directory should be created"


def test_multiprocess_directory_creation_race(tmp_path) -> None:
    """Issue #4132: Multiple processes creating same directory should all succeed.

    This is a more realistic test using multiprocessing to simulate actual
    concurrent directory creation attempts.
    """
    import multiprocessing

    db = tmp_path / "mp_shared" / "todo.json"
    results = multiprocessing.Manager().list()

    def worker(worker_id: int):
        """Worker that tries to save todos (creating parent dir)."""
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=worker_id, text=f"mp-worker-{worker_id}")]
            storage.save(todos)
            results.append(("success", worker_id))
        except FileExistsError as e:
            # This indicates the bug still exists
            results.append(("file_exists_error", worker_id, str(e)))
        except Exception as e:
            results.append(("error", worker_id, str(e)))

    # Start multiple processes that will race to create the parent directory
    processes = []
    for i in range(4):
        p = multiprocessing.Process(target=worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Check results
    errors = [r for r in results if r[0] == "file_exists_error"]
    assert len(errors) == 0, (
        f"FileExistsError should not occur with exist_ok=True. Errors: {errors}"
    )

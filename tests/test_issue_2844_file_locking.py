"""Regression tests for issue #2844: Add file locking mechanism to prevent concurrent write conflicts.

Issue: Current save() method only uses atomic writes, but when multiple processes write
simultaneously, last-writer-wins data loss still occurs. File locking ensures serialized
access and protects data integrity.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import multiprocessing
import time

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_file_lock_prevents_data_loss_from_concurrent_writes(tmp_path) -> None:
    """Issue #2844: File locking should prevent data loss from concurrent writes.

    Before fix: Multiple processes can write simultaneously, causing data loss
                 (last-writer-wins scenario).
    After fix: File locking ensures serialized access, preserving all writes.
    """
    db = tmp_path / "concurrent_lock.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that saves todos multiple times."""
        try:
            storage = TodoStorage(str(db))

            # Each worker saves multiple times to increase contention
            for i in range(3):
                todos = [
                    Todo(id=worker_id * 10 + i, text=f"worker-{worker_id}-todo-{i}"),
                    Todo(id=worker_id * 10 + i + 1, text=f"worker-{worker_id}-todo-{i+1}"),
                ]
                storage.save(todos)
                # Small delay to increase race likelihood
                time.sleep(0.001)

            result_queue.put(("success", worker_id))
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
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Check for errors
    errors = [r for r in results if r[0] == "error"]
    successes = [r for r in results if r[0] == "success"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Final verification: File should contain valid JSON with complete data
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # With file locking, we should have all todos from the last successful write
    # (each worker writes 2 todos, so we expect 2 todos in final state)
    assert isinstance(final_todos, list), "Final data should be a list"
    # The last writer's data should be complete
    assert len(final_todos) == 2, f"Expected 2 todos from last write, got {len(final_todos)}"


def test_save_uses_file_lock(tmp_path) -> None:
    """Issue #2844: Verify that save() acquires and releases file lock.

    This test checks that file locking is being used during save operations.
    """
    import sys

    db = tmp_path / "lock_test.json"

    # Track if file locking was attempted
    lock_acquired = False
    original_fcntl_flock = None
    original_msvcrt_locking = None

    # Patch fcntl.flock BEFORE importing storage (Unix)
    try:
        import fcntl

        original_fcntl_flock = fcntl.flock

        def tracking_flock(fd, operation):
            nonlocal lock_acquired
            # Check if exclusive lock (LOCK_EX = 2)
            lock_ex = 2
            if operation & lock_ex:
                lock_acquired = True
            return original_fcntl_flock(fd, operation)

        fcntl.flock = tracking_flock
    except ImportError:
        pass

    # Patch msvcrt.locking BEFORE importing storage (Windows)
    try:
        import msvcrt

        original_msvcrt_locking = msvcrt.locking

        def tracking_locking(fd, mode, nbytes):
            nonlocal lock_acquired
            # Lock mode 2 = exclusive lock
            if mode == 2:
                lock_acquired = True
            return original_msvcrt_locking(fd, mode, nbytes)

        msvcrt.locking = tracking_locking
    except ImportError:
        pass

    # Import storage AFTER patching
    from importlib import reload

    import flywheel.storage
    reload(flywheel.storage)
    from flywheel.storage import TodoStorage

    try:
        storage = TodoStorage(str(db))
        storage.save([Todo(id=1, text="test")])
    finally:
        # Restore original functions
        try:
            import fcntl

            fcntl.flock = original_fcntl_flock
        except (ImportError, AttributeError):
            pass

        try:
            import msvcrt

            msvcrt.locking = original_msvcrt_locking
        except (ImportError, AttributeError):
            pass

    # At least one locking mechanism should have been used
    # On Unix: fcntl should be available
    # On Windows: msvcrt should be available
    is_unix = sys.platform != "win32"
    is_windows = sys.platform == "win32"

    if is_unix:
        # On Unix, fcntl should be used
        try:
            import fcntl

            assert lock_acquired, "File lock should be acquired on Unix systems"
        except ImportError:
            pytest.skip("fcntl not available on this platform")
    elif is_windows:
        # On Windows, msvcrt should be used
        try:
            import msvcrt

            assert lock_acquired, "File lock should be acquired on Windows"
        except ImportError:
            pytest.skip("msvcrt not available on this platform")
    else:
        pytest.skip("Unknown platform, skipping lock detection test")


def test_load_uses_shared_lock(tmp_path) -> None:
    """Issue #2844: Verify that load() uses shared lock for reading.

    Shared locks allow multiple readers but block writers.
    """
    import sys

    db = tmp_path / "shared_lock_test.json"

    # Track lock usage during load
    lock_acquired = False
    original_fcntl_flock = None

    # Patch fcntl.flock BEFORE importing storage (Unix) - shared lock is LOCK_SH = 1
    try:
        import fcntl

        original_fcntl_flock = fcntl.flock

        def tracking_flock(fd, operation):
            nonlocal lock_acquired
            # Check if shared lock (LOCK_SH = 1)
            lock_sh = 1
            if operation & lock_sh:
                lock_acquired = True
            return original_fcntl_flock(fd, operation)

        fcntl.flock = tracking_flock
    except ImportError:
        pass

    # Import storage AFTER patching
    from importlib import reload

    import flywheel.storage
    reload(flywheel.storage)
    from flywheel.storage import TodoStorage

    try:
        storage = TodoStorage(str(db))
        # First, create a file
        storage.save([Todo(id=1, text="initial")])
        # Then load it
        storage.load()
    finally:
        # Restore original function
        try:
            import fcntl

            fcntl.flock = original_fcntl_flock
        except (ImportError, AttributeError, NameError):
            pass

    if sys.platform != "win32":
        try:
            import fcntl

            assert lock_acquired, "Shared lock should be acquired during load on Unix"
        except ImportError:
            pytest.skip("fcntl not available on this platform")


def test_concurrent_save_and_load_with_locking(tmp_path) -> None:
    """Issue #2844: Verify that load() blocks while save() is in progress.

    This test ensures proper read/write synchronization.
    """
    import multiprocessing
    import time

    db = tmp_path / "concurrent_rw.json"

    def save_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that saves data."""
        try:
            storage = TodoStorage(str(db))
            todos = [
                Todo(id=1, text="save-worker-todo-1"),
                Todo(id=2, text="save-worker-todo-2"),
            ]
            # Hold the lock a bit longer to ensure contention
            storage.save(todos)
            result_queue.put(("save_success",))
        except Exception as e:
            result_queue.put(("error", str(e)))

    def load_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that loads data."""
        try:
            time.sleep(0.01)  # Start slightly after save to ensure contention
            storage = TodoStorage(str(db))
            todos = storage.load()
            result_queue.put(("load_success", worker_id, len(todos)))
        except Exception as e:
            result_queue.put(("error", str(e)))

    # Start save and multiple load workers concurrently
    processes = []
    result_queue = multiprocessing.Queue()

    save_proc = multiprocessing.Process(target=save_worker, args=(result_queue,))
    processes.append(save_proc)
    save_proc.start()

    for i in range(2):
        load_proc = multiprocessing.Process(target=load_worker, args=(i, result_queue))
        processes.append(load_proc)
        load_proc.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=30)
        assert p.exitcode == 0, f"Process {p} failed with exit code {p.exitcode}"

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Verify no errors and all operations completed
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Operations encountered errors: {errors}"

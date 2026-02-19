"""Regression tests for issue #4508: TOCTOU race condition in _ensure_parent_directory.

Issue: _ensure_parent_directory has two TOCTOU race conditions:
1. part.exists() followed by part.is_dir() - separate system calls with race window
2. parent.exists() followed by mkdir() - another process could create between check and mkdir

Fix: Use atomic mkdir(parents=True, exist_ok=True) and catch FileExistsError.
"""

from __future__ import annotations

import multiprocessing

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_atomic_mkdir_handles_concurrent_creation(tmp_path) -> None:
    """Issue #4508: Test that concurrent directory creation doesn't cause errors.

    Before fix: exists() check could pass, then mkdir() could fail if another
    process created the directory in between (FileExistsError with exist_ok=False).

    After fix: Using mkdir(parents=True, exist_ok=True) handles this atomically.
    """
    db_path = tmp_path / "subdir1" / "subdir2" / "todo.json"

    def create_parent_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that calls _ensure_parent_directory concurrently."""
        try:
            # All workers try to ensure the same parent directory exists
            _ensure_parent_directory(db_path)
            result_queue.put(("success", worker_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=create_parent_worker, args=(i, result_queue))
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

    # All workers should succeed (no TOCTOU race)
    assert len(errors) == 0, f"Workers encountered TOCTOU race errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"


def test_atomic_mkdir_with_storage_save_concurrent(tmp_path) -> None:
    """Issue #4508: Test concurrent TodoStorage.save() doesn't cause TOCTOU errors.

    Multiple processes saving to the same parent directory should all succeed
    without FileExistsError or other race-related failures.
    """
    db_path = tmp_path / "deep" / "nested" / "path" / "todo.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves todos to the same path concurrently."""
        try:
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=1, text=f"worker-{worker_id}")]
            storage.save(todos)
            result_queue.put(("success", worker_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
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

    # All workers should succeed
    assert len(errors) == 0, f"Workers encountered race condition errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"


def test_file_as_directory_error_still_clear(tmp_path) -> None:
    """Issue #4508: Verify that file-as-directory error message is still clear after fix.

    The fix should still provide clear error messages when a parent path component
    is a file (not a directory), just using a different code path.
    """
    # Create a file where we expect a directory
    conflicting_file = tmp_path / "blocking.txt"
    conflicting_file.write_text("I am a file, not a directory")

    # Try to create db at path that would require the file to be a directory
    db_path = conflicting_file / "subdir" / "todo.json"

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
        _ensure_parent_directory(db_path)


def test_immediate_parent_is_file_error(tmp_path) -> None:
    """Issue #4508: Immediate parent being a file should raise clear error."""
    # Create a file at parent location
    parent_file = tmp_path / "parent.json"
    parent_file.write_text("{}")

    # Try to create database inside what is actually a file
    db_path = parent_file / "data.json"

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
        _ensure_parent_directory(db_path)


def test_normal_nested_directory_creation_still_works(tmp_path) -> None:
    """Issue #4508: Normal nested directory creation should still work."""
    db_path = tmp_path / "a" / "b" / "c" / "d" / "todo.json"

    # Should not raise
    _ensure_parent_directory(db_path)

    # Parent directory should exist
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_existing_parent_directory_is_fine(tmp_path) -> None:
    """Issue #4508: Should work fine when parent directory already exists."""
    # Pre-create the parent directory
    parent_dir = tmp_path / "existing"
    parent_dir.mkdir(parents=True)

    db_path = parent_dir / "todo.json"

    # Should not raise
    _ensure_parent_directory(db_path)

    # Parent should still exist and be a directory
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_no_toctou_pattern_exists_followed_by_is_dir() -> None:
    """Issue #4508: Verify no TOCTOU pattern 'exists() and not is_dir()' in source code.

    The fix should eliminate the TOCTOU race by using is_dir() directly instead of
    the pattern 'part.exists() and not part.is_dir()' which creates a race window
    between the two system calls.
    """
    import ast
    import inspect

    source = inspect.getsource(_ensure_parent_directory)
    tree = ast.parse(source)

    class TOCTOUChecker(ast.NodeVisitor):
        def __init__(self):
            self.has_toctou_pattern = False
            self.toctou_locations = []

        def visit_BoolOp(self, node):
            """Check for 'exists() and not is_dir()' pattern."""
            if isinstance(node.op, ast.And):
                for value in node.values:
                    # Check for call to .exists()
                    if (
                        isinstance(value, ast.Call)
                        and isinstance(value.func, ast.Attribute)
                        and value.func.attr == "exists"
                    ):
                        # Check if another value is "not .is_dir()"
                        for other_value in node.values:
                            if (
                                isinstance(other_value, ast.UnaryOp)
                                and isinstance(other_value.op, ast.Not)
                                and isinstance(other_value.operand, ast.Call)
                                and isinstance(other_value.operand.func, ast.Attribute)
                                and other_value.operand.func.attr == "is_dir"
                            ):
                                self.has_toctou_pattern = True
                                self.toctou_locations.append(node.lineno)
            self.generic_visit(node)

    checker = TOCTOUChecker()
    checker.visit(tree)

    assert not checker.has_toctou_pattern, (
        f"TOCTOU race condition pattern found at lines {checker.toctou_locations}: "
        "'exists() and not is_dir()' creates a race window between two system calls. "
        "Use 'not is_dir()' directly instead, since is_dir() returns False for non-existent paths."
    )

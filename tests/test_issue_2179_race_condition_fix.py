"""Regression tests for issue #2179: Race condition in _ensure_parent_directory.

Issue: The exist_ok=False in mkdir() causes FileExistsError when multiple
processes try to create the same parent directory concurrently.

The race condition occurs:
1. Process A checks parent.exists() -> False
2. Process B checks parent.exists() -> False
3. Process A calls mkdir() -> succeeds
4. Process B calls mkdir() -> FileExistsError

These tests verify that concurrent directory creation works correctly.
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import _ensure_parent_directory

# Global path for multiprocessing - must be set before spawning processes
_test_path_str: str | None = None


def _create_parent_in_process(_: int) -> tuple[bool, str | None]:
    """Helper function for multiprocessing - must be at module level.

    Uses global _test_path_str to get the path to create.
    """
    global _test_path_str
    if _test_path_str is None:
        return (False, "Test path not set")

    try:
        _ensure_parent_directory(Path(_test_path_str))
        return (True, None)
    except FileExistsError as e:
        return (False, f"FileExistsError: {e}")
    except Exception as e:
        return (False, f"{type(e).__name__}: {e}")


def test_concurrent_directory_creation_same_path() -> None:
    """Issue #2179: Multiple processes creating the same parent directory should succeed.

    This test spawns multiple processes that all try to create the same
    parent directory concurrently. With the bug (exist_ok=False), at least
    one process will fail with FileExistsError. With the fix (exist_ok=True),
    all processes should succeed.
    """
    global _test_path_str
    with tempfile.TemporaryDirectory() as tmp_dir:
        # All processes will try to create the same parent directory
        test_path = Path(tmp_dir) / "race_test" / "subdir" / "todo.json"
        _test_path_str = str(test_path)

        try:
            # Run multiple processes concurrently
            num_processes = 5
            with multiprocessing.Pool(processes=num_processes) as pool:
                results = pool.map(_create_parent_in_process, range(num_processes))

            # All processes should succeed
            successes = [r for r, _ in results if r]
            failures = [(i, err) for i, (r, err) in enumerate(results) if not r]

            assert len(successes) == num_processes, (
                f"Expected all {num_processes} processes to succeed, "
                f"but got {len(successes)} successes and {len(failures)} failures. "
                f"Failures: {failures}"
            )
        finally:
            _test_path_str = None


# Global path for concurrent save test
_save_test_path_str: str | None = None


def _try_save_in_process(process_id: int) -> tuple[bool, str | None]:
    """Helper function for multiprocessing - must be at module level.

    Uses global _save_test_path_str to get the database path.
    """
    global _save_test_path_str
    if _save_test_path_str is None:
        return (False, "Test path not set")

    try:
        from flywheel.storage import TodoStorage
        from flywheel.todo import Todo
        storage = TodoStorage(_save_test_path_str)
        storage.save([Todo(id=1, text=f"Process {process_id}")])
        return (True, None)
    except FileExistsError as e:
        return (False, f"FileExistsError: {e}")
    except Exception as e:
        # Other errors (like file locking) are acceptable
        return (True, f"Acceptable error: {type(e).__name__}")


def test_storage_save_concurrent_same_parent() -> None:
    """Issue #2179: TodoStorage.save() should handle concurrent directory creation.

    Multiple processes trying to save to the same database path concurrently
    should all succeed (or fail due to file locking, but not FileExistsError).
    """
    global _save_test_path_str
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "concurrent" / "todo.json"
        _save_test_path_str = str(db_path)

        try:
            num_processes = 3
            with multiprocessing.Pool(processes=num_processes) as pool:
                results = pool.map(_try_save_in_process, range(num_processes))

            # Check that FileExistsError was not raised
            file_exists_errors = [
                err for success, err in results if not success and err and "FileExistsError" in err
            ]

            assert len(file_exists_errors) == 0, (
                f"FileExistsError should not occur in concurrent scenarios. "
                f"Got {len(file_exists_errors)} FileExistsError(s): {file_exists_errors}"
            )
        finally:
            _save_test_path_str = None


def test_ensure_parent_with_file_conflict_still_detected() -> None:
    """Issue #2179: The fix should not break file-as-directory detection.

    Even with exist_ok=True, the validation loop should still prevent
    using a file as a directory.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a file at parent location
        blocking_file = Path(tmp_dir) / "blocking.json"
        blocking_file.write_text("I am a file")

        # Try to create a path that needs the "file" to be a directory
        test_path = blocking_file / "subdir" / "todo.json"

        # Should still raise ValueError (file-as-directory confusion)
        with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
            _ensure_parent_directory(test_path)


def test_ensure_parent_normal_case() -> None:
    """Issue #2179: Normal directory creation should still work."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_path = Path(tmp_dir) / "normal" / "nested" / "todo.json"

        _ensure_parent_directory(test_path)

        # Parent should be created
        assert test_path.parent.exists()
        assert test_path.parent.is_dir()


def test_ensure_parent_idempotent() -> None:
    """Issue #2179: Calling _ensure_parent_directory multiple times should be safe."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_path = Path(tmp_dir) / "idempotent" / "todo.json"

        # Call multiple times - should not fail
        _ensure_parent_directory(test_path)
        _ensure_parent_directory(test_path)
        _ensure_parent_directory(test_path)

        assert test_path.parent.exists()

"""Regression tests for issue #6590: TOCTOU race condition in _ensure_parent_directory.

Issue: The check-then-create pattern in _ensure_parent_directory has a race condition:
1. Line 43: if not parent.exists()  -- check
2. Line 45: parent.mkdir(exist_ok=False)  -- create with exist_ok=False

Between check and create, another process could create the directory, causing
FileExistsError with exist_ok=False.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import ast
import inspect
import multiprocessing

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_mkdir_uses_exist_ok_true_to_avoid_toctou_race() -> None:
    """Issue #6590: Verify that _ensure_parent_directory uses exist_ok=True.

    This test directly verifies the fix by inspecting the code behavior.
    With exist_ok=False (bug): TOCTOU race can cause FileExistsError.
    With exist_ok=True (fix): mkdir is safe even if directory appears between check and create.
    """
    # Get the source code of _ensure_parent_directory
    source = inspect.getsource(_ensure_parent_directory)

    # Parse and find the mkdir call
    tree = ast.parse(source)

    class MkdirCallVisitor(ast.NodeVisitor):
        def __init__(self):
            self.mkdir_calls = []

        def visit_Call(self, node):
            # Look for .mkdir() calls
            if isinstance(node.func, ast.Attribute) and node.func.attr == "mkdir":
                # Find exist_ok keyword argument
                for keyword in node.keywords:
                    if keyword.arg == "exist_ok" and isinstance(
                        keyword.value, ast.Constant
                    ):
                        self.mkdir_calls.append(keyword.value.value)
            self.generic_visit(node)

    visitor = MkdirCallVisitor()
    visitor.visit(tree)

    # Verify that mkdir is called with exist_ok=True
    assert len(visitor.mkdir_calls) > 0, "mkdir should have exist_ok argument"
    assert all(v is True for v in visitor.mkdir_calls), (
        f"All mkdir calls should use exist_ok=True to handle TOCTOU race. "
        f"Got: {visitor.mkdir_calls}"
    )


def test_toctou_race_simulated_by_forced_directory_creation(tmp_path) -> None:
    """Issue #6590: Verify that exist_ok=True handles directory-already-exists case.

    Direct test: call _ensure_parent_directory when directory exists.
    With exist_ok=False this would fail; with exist_ok=True it succeeds.
    """
    target_file = tmp_path / "existing_dir" / "file.json"

    # Pre-create the parent directory
    target_file.parent.mkdir(parents=True, exist_ok=True)

    # This should succeed without raising FileExistsError
    # If exist_ok=False is used internally, this would raise FileExistsError
    _ensure_parent_directory(target_file)

    # Verify directory still exists
    assert target_file.parent.is_dir()


def test_concurrent_save_creates_parent_directory_without_error(tmp_path) -> None:
    """Issue #6590: Concurrent saves to non-existent path should not fail with FileExistsError.

    Multiple processes trying to save to the same new path (where parent doesn't exist)
    should all succeed without FileExistsError from mkdir race condition.
    """
    db = tmp_path / "newdir" / "concurrent.json"

    # Ensure parent doesn't exist at start
    assert not db.parent.exists()

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves to a path requiring directory creation."""
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
            result_queue.put(("success", worker_id))
        except FileExistsError as e:
            # This is the specific error from the TOCTOU bug
            result_queue.put(("file_exists_error", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
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

    # No worker should have encountered FileExistsError
    file_exists_errors = [r for r in results if r[0] == "file_exists_error"]
    assert len(file_exists_errors) == 0, (
        f"Workers hit TOCTOU race condition (FileExistsError): {file_exists_errors}"
    )

    # All workers should succeed (though last-writer-wins)
    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}. Results: {results}"
    )

    # Final file should be valid JSON
    storage = TodoStorage(str(db))
    loaded = storage.load()
    assert len(loaded) >= 1


def test_ensure_parent_directory_is_idempotent(tmp_path) -> None:
    """Issue #6590: Calling _ensure_parent_directory multiple times should be safe.

    If exist_ok=False is used, second call would fail with FileExistsError.
    With exist_ok=True, it's idempotent.
    """
    target_file = tmp_path / "testdir" / "file.json"

    # First call - creates directory
    _ensure_parent_directory(target_file)
    assert target_file.parent.is_dir()

    # Second call - should be idempotent (no error)
    _ensure_parent_directory(target_file)
    assert target_file.parent.is_dir()

    # Third call for good measure
    _ensure_parent_directory(target_file)
    assert target_file.parent.is_dir()

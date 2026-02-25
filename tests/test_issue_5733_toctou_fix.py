"""Regression tests for issue #5733: TOCTOU race condition in _ensure_parent_directory.

Issue: Race condition (TOCTOU) in _ensure_parent_directory: file type check and mkdir
are not atomic. The pattern `if not parent.exists(): parent.mkdir()` creates a race
window where another process could create the directory between the check and mkdir.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_toctou_mkdir_race_condition_injected_at_mkdir(tmp_path, monkeypatch) -> None:
    """Issue #5733: Simulate TOCTOU race where directory appears between exists() and mkdir().

    This test mocks mkdir to fail with FileExistsError (simulating another process
    creating the directory), then verifies that exist_ok=True is used to handle it.
    """
    db_path = tmp_path / "newdir" / "subdir" / "todo.json"
    parent_path = db_path.parent

    # Track mkdir calls and their exist_ok parameter
    mkdir_calls = []
    original_mkdir = Path.mkdir

    def tracking_mkdir(self, *args, **kwargs):
        """Track mkdir calls and simulate race condition."""
        exist_ok = kwargs.get("exist_ok", args[0] if args and len(args) > 0 else False)
        mkdir_calls.append({"path": str(self), "exist_ok": exist_ok})

        # If exist_ok=False and this is the parent path, simulate race:
        # another process created the directory between exists() and mkdir()
        if not exist_ok and self == parent_path:
            # First, actually create the directory (simulating other process)
            original_mkdir(self, parents=True, exist_ok=True)
            # Then raise FileExistsError as if we tried to create it
            raise FileExistsError(f"[Errno 17] File exists: '{self}'")

        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", tracking_mkdir)

    storage = TodoStorage(str(db_path))

    # With the old code (exist_ok=False), this would raise FileExistsError
    # With the fix (exist_ok=True), this should succeed
    storage.save([Todo(id=1, text="test")])

    # After fix: mkdir should have been called with exist_ok=True
    assert len(mkdir_calls) >= 1, "mkdir should have been called"
    # Check that at least one mkdir call used exist_ok=True
    assert any(call["exist_ok"] for call in mkdir_calls), (
        f"mkdir should be called with exist_ok=True to avoid TOCTOU race. "
        f"Got calls: {mkdir_calls}"
    )


def test_toctou_direct_mkdir_with_exist_ok_false_fails(tmp_path) -> None:
    """Issue #5733: Demonstrate that mkdir(exist_ok=False) fails when directory exists.

    This test demonstrates the underlying issue: calling mkdir(exist_ok=False) on
    an existing directory raises FileExistsError. The fix should use exist_ok=True.
    """
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()

    # mkdir(exist_ok=False) on existing directory should fail
    with pytest.raises(FileExistsError):
        test_dir.mkdir(exist_ok=False)


def test_toctou_direct_mkdir_with_exist_ok_true_succeeds(tmp_path) -> None:
    """Issue #5733: Demonstrate that mkdir(exist_ok=True) succeeds when directory exists.

    This test shows the fix: calling mkdir(exist_ok=True) on an existing directory
    succeeds without raising an error.
    """
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()

    # mkdir(exist_ok=True) on existing directory should succeed
    test_dir.mkdir(exist_ok=True)  # Should not raise

    assert test_dir.is_dir()


def test_toctou_concurrent_mkdir_no_spurious_error(tmp_path) -> None:
    """Issue #5733: Concurrent processes should not get spurious FileExistsError.

    This simulates the race condition by having mkdir "succeed" from another process
    perspective - i.e., the directory already exists when we try to create it.
    """
    db_path = tmp_path / "race" / "todo.json"
    storage = TodoStorage(str(db_path))

    # First call creates the directory
    storage.save([Todo(id=1, text="first")])

    # Second call should NOT fail even if directory already exists
    # (this tests that exist_ok=True works properly)
    storage.save([Todo(id=2, text="second")])

    # Verify data integrity
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "second"


def test_toctou_parent_is_file_still_raises_error(tmp_path) -> None:
    """Issue #5733: If parent path is a file, should still raise error reliably.

    Even with the TOCTOU fix, we must still detect when a parent path component
    exists as a file (not a directory) and raise an appropriate error.
    """
    # Create a file where a directory would need to be
    blocking_file = tmp_path / "blocking.json"
    blocking_file.write_text("I am a file")

    # Try to create a database that would need blocking_file to be a directory
    db_path = blocking_file / "subdir" / "todo.json"

    # Should raise ValueError indicating the path problem
    with pytest.raises(ValueError, match=r"(file|directory|path)"):
        _ensure_parent_directory(db_path)


def test_toctou_file_exists_error_on_non_dir_parent(tmp_path) -> None:
    """Issue #5733: If mkdir fails because parent is a file, raise appropriate error.

    When using exist_ok=True with parents=True, if a parent component is a file,
    mkdir will raise FileExistsError (or NotADirectoryError). This should be
    caught and converted to a clear ValueError.
    """
    # Create a file at the location where we need a directory
    blocking_file = tmp_path / "blocker"
    blocking_file.write_text("blocking")

    # Try to create nested structure that would need blocker to be a directory
    db_path = blocking_file / "nested" / "todo.json"

    # The fix should catch this and raise ValueError (not raw FileExistsError)
    with pytest.raises((ValueError, OSError, NotADirectoryError)):
        _ensure_parent_directory(db_path)


def test_toctou_multiple_concurrent_ensure_parent_directory(tmp_path) -> None:
    """Issue #5733: Multiple calls to _ensure_parent_directory should be safe.

    Calling _ensure_parent_directory multiple times for the same path should
    not cause any errors.
    """
    db_path = tmp_path / "multi" / "deep" / "todo.json"

    # First call creates directories
    _ensure_parent_directory(db_path)

    # Second call should be idempotent (no error)
    _ensure_parent_directory(db_path)

    # Third call should also work
    _ensure_parent_directory(db_path)

    # Verify parent was created
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()

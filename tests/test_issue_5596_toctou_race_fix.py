"""Regression tests for issue #5596: TOCTOU race in _ensure_parent_directory.

Issue: _ensure_parent_directory() validates parent path components then
calls mkdir separately, leaving a race window where an attacker could
create a symlink between validation and directory creation.

Fix: Use exist_ok=True with post-hoc symlink validation to eliminate
the TOCTOU race while maintaining symlink attack protection.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from flywheel.storage import _ensure_parent_directory


def test_ensure_parent_directory_is_idempotent_with_exist_ok(tmp_path: Path) -> None:
    """Issue #5596: mkdir with exist_ok=True should succeed when directory already exists.

    This tests that the fix handles the case where the directory is created
    between the check and the mkdir (race condition).
    """
    db_path = tmp_path / "subdir" / "todo.json"

    # First call should create the directory
    _ensure_parent_directory(db_path)
    assert db_path.parent.exists()

    # Second call should succeed without error (idempotent)
    # This simulates the race condition where directory appears after check
    _ensure_parent_directory(db_path)
    assert db_path.parent.exists()


def test_ensure_parent_directory_handles_concurrent_creation(tmp_path: Path) -> None:
    """Issue #5596: Concurrent directory creation should not cause errors.

    Simulates multiple threads trying to create the same parent directory.
    Before fix: One thread could fail with FileExistsError if another creates
    the directory between the exists() check and mkdir().
    After fix: All threads should succeed with exist_ok=True.
    """
    db_path = tmp_path / "shared" / "todo.json"
    errors = []
    successes = []

    def create_parent():
        try:
            _ensure_parent_directory(db_path)
            successes.append(1)
        except Exception as e:
            errors.append(e)

    # Run multiple threads concurrently
    threads = [threading.Thread(target=create_parent) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All threads should succeed (no TOCTOU race errors)
    assert len(errors) == 0, f"Threads encountered errors: {errors}"
    assert len(successes) == 10
    assert db_path.parent.exists()


def test_ensure_parent_directory_still_rejects_file_as_parent(tmp_path: Path) -> None:
    """Issue #5596: Fix must maintain symlink/file-as-directory protection.

    The fix should still reject cases where a parent path component is
    a file (not a directory), which would cause path confusion attacks.
    """
    # Create a file where a directory is expected
    blocking_file = tmp_path / "blocking.txt"
    blocking_file.write_text("I am a file")

    # Try to create a db path that requires the file to be a directory
    db_path = blocking_file / "subdir" / "todo.json"

    # Should fail with clear error about file vs directory
    with pytest.raises(ValueError, match=r"(file|directory|not a directory)"):
        _ensure_parent_directory(db_path)


def test_ensure_parent_directory_rejects_symlink_traversal(tmp_path: Path) -> None:
    """Issue #5596: Post-hoc validation should detect symlink traversal attacks.

    After mkdir succeeds, verify that no symlinks were traversed in the path.
    This prevents an attacker from creating a symlink in the race window
    that would cause writes to an unexpected location.
    """
    # Create a symlink that points outside the intended directory
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    link_dir = tmp_path / "link"
    link_dir.symlink_to(target_dir)

    # Create a db path that goes through the symlink
    db_path = link_dir / "todo.json"

    # Should fail with clear error about symlink
    with pytest.raises(ValueError, match=r"(?i)symlink"):
        _ensure_parent_directory(db_path)


def test_ensure_parent_directory_allows_legitimate_nested_paths(tmp_path: Path) -> None:
    """Issue #5596: Normal nested directory creation should still work.

    Verify the fix doesn't break normal use cases for deeply nested paths.
    """
    db_path = tmp_path / "a" / "b" / "c" / "d" / "todo.json"

    # Should succeed without error
    _ensure_parent_directory(db_path)
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()

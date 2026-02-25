"""Regression tests for issue #5693: Symlink security vulnerability in _ensure_parent_directory.

Issue: _ensure_parent_directory() uses exists() and is_dir() which follow symlinks,
allowing TOCTOU race condition and symlink-based attacks.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os

import pytest

from flywheel.storage import TodoStorage


def test_storage_fails_when_parent_is_symlink_to_file(tmp_path) -> None:
    """Issue #5693: Should fail when parent path component is a symlink to a file.

    Before fix: exists() follows symlink, sees target exists; is_dir() follows symlink,
    returns False (target is file) - but this doesn't detect the symlink itself.
    After fix: Should detect symlink in parent path and raise appropriate error.
    """
    # Create a file
    target_file = tmp_path / "actual_file.txt"
    target_file.write_text("I am a file")

    # Create a symlink pointing to the file
    symlink_path = tmp_path / "symlink_to_file"
    symlink_path.symlink_to(target_file)

    # Try to create db path that traverses through the symlink
    db_path = symlink_path / "subdir" / "todo.json"

    storage = TodoStorage(str(db_path))

    # Should fail with clear error about symlink
    with pytest.raises((ValueError, OSError), match=r"(symlink|symbolic link)"):
        storage.save([])


def test_storage_fails_when_parent_is_symlink_to_directory(tmp_path) -> None:
    """Issue #5693: Should fail when parent path component is a symlink to a directory.

    Before fix: exists() follows symlink, sees directory; is_dir() follows symlink,
    returns True - passes the check but allows symlink traversal.
    After fix: Should detect symlink in parent path and raise appropriate error.
    """
    # Create a directory
    target_dir = tmp_path / "actual_directory"
    target_dir.mkdir()

    # Create a symlink pointing to the directory
    symlink_path = tmp_path / "symlink_to_dir"
    symlink_path.symlink_to(target_dir)

    # Try to create db path that traverses through the symlink
    db_path = symlink_path / "todo.json"

    storage = TodoStorage(str(db_path))

    # Should fail with clear error about symlink
    with pytest.raises((ValueError, OSError), match=r"(symlink|symbolic link)"):
        storage.save([])


def test_storage_fails_when_deep_parent_is_symlink(tmp_path) -> None:
    """Issue #5693: Should detect symlink even in deep parent path.

    This tests the case where a symlink is in the middle of the parent chain.
    """
    # Create structure: target_dir/file.txt
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    (target_dir / "file.txt").write_text("content")

    # Create symlink pointing to target
    symlink_dir = tmp_path / "link"
    symlink_dir.symlink_to(target_dir)

    # Try to create db at: link/file.txt/db.json
    # This would traverse through symlink -> target_dir -> file.txt (which is a file)
    db_path = symlink_dir / "file.txt" / "db.json"

    storage = TodoStorage(str(db_path))

    # Should fail - detecting symlink in parent chain
    with pytest.raises((ValueError, OSError)):
        storage.save([])


def test_storage_succeeds_with_no_symlinks_in_path(tmp_path) -> None:
    """Issue #5693: Normal paths without symlinks should still work."""
    db_path = tmp_path / "normal" / "path" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should succeed - no symlinks
    storage.save([])

    # Verify file was created
    assert db_path.exists()


def test_storage_detects_broken_symlink_in_parent_path(tmp_path) -> None:
    """Issue #5693: Should fail when parent is a broken symlink (dangling symlink)."""
    # Create a symlink to a non-existent target
    symlink_path = tmp_path / "broken_symlink"
    symlink_path.symlink_to(tmp_path / "non_existent_target")

    # Try to create db path through the broken symlink
    db_path = symlink_path / "todo.json"

    storage = TodoStorage(str(db_path))

    # Should fail - symlink detected
    with pytest.raises((ValueError, OSError)):
        storage.save([])

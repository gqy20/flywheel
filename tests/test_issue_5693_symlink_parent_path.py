"""Regression tests for issue #5693: Symlink TOCTOU in _ensure_parent_directory().

Issue: _ensure_parent_directory() uses exists() and is_dir() which follow symlinks,
allowing TOCTOU race condition. A symlink to a file in parent path could be exploited.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_ensure_parent_directory_fails_when_parent_is_symlink_to_file(tmp_path) -> None:
    """Issue #5693: Should fail when a parent component is a symlink to a file.

    Before fix: exists() and is_dir() follow symlinks, so symlink to file
                would be detected (is_dir returns False), but the check is
                vulnerable to TOCTOU race condition
    After fix: Should use lstat() to not follow symlinks, detecting them explicitly
    """
    # Create a regular file
    target_file = tmp_path / "regular_file.txt"
    target_file.write_text("I am a regular file")

    # Create a symlink pointing to the file
    symlink_dir = tmp_path / "symlink_dir"
    os.symlink(target_file, symlink_dir)  # symlink_dir -> regular_file.txt

    # Try to create a db path that traverses through the symlink
    db_path = symlink_dir / "subdir" / "todo.json"

    storage = TodoStorage(str(db_path))

    # Should fail with appropriate error about symlink
    with pytest.raises(ValueError, match=r"(symlink|symbolic link)"):
        storage.save([])


def test_ensure_parent_directory_fails_when_parent_is_symlink_to_directory(tmp_path) -> None:
    """Issue #5693: Should fail when a parent component is a symlink to a directory.

    Even though a symlink to a directory behaves like a directory, we should
    reject it to prevent symlink-based attacks and TOCTOU races.
    """
    # Create a regular directory
    target_dir = tmp_path / "real_directory"
    target_dir.mkdir()

    # Create a symlink pointing to the directory
    symlink_dir = tmp_path / "symlink_to_dir"
    os.symlink(target_dir, symlink_dir)  # symlink_to_dir -> real_directory

    # Try to create a db path that traverses through the symlink
    db_path = symlink_dir / "subdir" / "todo.json"

    storage = TodoStorage(str(db_path))

    # Should fail with appropriate error about symlink
    with pytest.raises(ValueError, match=r"(symlink|symbolic link)"):
        storage.save([])


def test_ensure_parent_directory_succeeds_with_normal_directory(tmp_path) -> None:
    """Issue #5693: Normal directory creation should still work after the fix."""
    db_path = tmp_path / "normal_dir" / "subdir" / "todo.json"

    storage = TodoStorage(str(db_path))

    # Should succeed normally
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Verify content
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_ensure_parent_directory_detects_symlink_in_path_chain(tmp_path) -> None:
    """Issue #5693: Should detect symlink anywhere in the parent path chain."""
    # Create a directory structure with a symlink in the middle
    real_dir = tmp_path / "real_parent"
    real_dir.mkdir()

    # Create a symlink inside real_dir pointing to a file
    target_file = tmp_path / "target_file.txt"
    target_file.write_text("content")

    symlink_inside = real_dir / "symlink_inside"
    os.symlink(target_file, symlink_inside)

    # Try to create a db path that traverses through the symlink
    db_path = symlink_inside / "nested" / "todo.json"

    storage = TodoStorage(str(db_path))

    # Should fail with appropriate error about symlink
    with pytest.raises(ValueError, match=r"(symlink|symbolic link)"):
        storage.save([])


def test_ensure_parent_directory_uses_lstat_not_follow_symlinks(tmp_path) -> None:
    """Issue #5693: Verify that exists() and is_dir() don't follow symlinks.

    This test ensures that even if a symlink points to a valid directory,
    we use lstat-style checks that don't follow the symlink.
    """
    # Create a real directory with content
    real_dir = tmp_path / "real_directory"
    real_dir.mkdir()
    (real_dir / "existing_file.txt").write_text("content")

    # Create a symlink pointing to the real directory
    symlink_path = tmp_path / "symlink_to_real_dir"
    os.symlink(real_dir, symlink_path)

    # The symlink itself exists (via lstat)
    assert symlink_path.is_symlink() is True
    # exists() follows symlinks and would return True
    assert symlink_path.exists() is True
    # is_dir() follows symlinks and would return True (since target is a dir)
    assert symlink_path.is_dir() is True

    # But our code should detect the symlink and reject it
    db_path = symlink_path / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should fail because symlink_path is a symlink, even though it points to a valid directory
    with pytest.raises(ValueError, match=r"(symlink|symbolic link)"):
        storage.save([])


def test_ensure_parent_directory_dangling_symlink(tmp_path) -> None:
    """Issue #5693: Should detect and reject dangling symlinks in parent path."""
    # Create a symlink pointing to a non-existent target
    dangling_symlink = tmp_path / "dangling_link"
    os.symlink(tmp_path / "nonexistent_target", dangling_symlink)

    # The symlink exists (as a symlink) but the target doesn't
    assert dangling_symlink.is_symlink() is True
    assert dangling_symlink.exists() is False  # exists() follows and target doesn't exist

    db_path = dangling_symlink / "subdir" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should fail with symlink error, not file-as-directory error
    with pytest.raises(ValueError, match=r"(symlink|symbolic link)"):
        storage.save([])

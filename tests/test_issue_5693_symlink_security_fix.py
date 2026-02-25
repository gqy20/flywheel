"""Regression tests for issue #5693: Symlink security vulnerability in _ensure_parent_directory.

Issue: _ensure_parent_directory() uses exists() and is_dir() which follow symlinks,
allowing TOCTOU race condition and symlink attacks.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_ensure_parent_directory_fails_when_parent_is_symlink_to_file(tmp_path) -> None:
    """Issue #5693: Should fail with clear error when parent path is a symlink to a file.

    Security vulnerability: exists() and is_dir() follow symlinks, so a symlink to
    a directory returns True for is_dir(). This allows symlink attacks where an
    attacker can redirect writes to unintended locations.

    The fix should use os.path.lexists() or is_symlink() to detect symlinks
    without following them.
    """
    # Create a regular file
    target_file = tmp_path / "target_file.txt"
    target_file.write_text("sensitive data")

    # Create a symlink pointing to the file
    symlink_dir = tmp_path / "symlink_dir"
    symlink_dir.symlink_to(target_file)

    # Verify our test setup: symlink should exist but point to a file
    assert symlink_dir.exists()  # exists() follows symlinks
    assert not symlink_dir.is_dir()  # is_dir() also follows symlinks, should be False for file
    assert symlink_dir.is_symlink()  # But it IS a symlink

    # Try to create database at a path that traverses through the symlink
    # This should fail because the symlink points to a file, not a directory
    db_path = symlink_dir / "subdir" / "todo.json"

    storage = TodoStorage(str(db_path))

    # Should raise ValueError for symlink, not follow it silently
    # Note: This is the KEY security fix - we detect symlinks and reject them
    with pytest.raises(ValueError, match=r"(symlink|symbolic link)"):
        storage.save([])


def test_ensure_parent_directory_fails_when_parent_is_symlink_to_directory(tmp_path) -> None:
    """Issue #5693: Should fail when parent path contains a symlink to a directory.

    Even if the symlink points to a valid directory, we should not follow it
    to prevent symlink attacks where an attacker could redirect file writes.
    """
    # Create a target directory
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()

    # Create a symlink pointing to the directory
    symlink_in_path = tmp_path / "symlink_to_dir"
    symlink_in_path.symlink_to(target_dir)

    # Verify test setup
    assert symlink_in_path.is_symlink()
    assert symlink_in_path.is_dir()  # is_dir() follows symlinks and returns True for dir

    # Try to create database at a path that traverses through the symlink
    db_path = symlink_in_path / "todo.json"

    storage = TodoStorage(str(db_path))

    # Should raise an error about symlinks being disallowed in parent path
    with pytest.raises(ValueError, match=r"(symlink|symbolic link)"):
        storage.save([])


def test_ensure_parent_directory_allows_normal_directories(tmp_path) -> None:
    """Issue #5693: Normal directory paths should still work after the fix."""
    # Create a nested directory structure
    nested_dir = tmp_path / "level1" / "level2" / "level3"
    nested_dir.mkdir(parents=True)

    db_path = nested_dir / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should succeed for normal paths
    storage.save([])
    assert db_path.exists()


def test_ensure_parent_directory_creates_new_directories(tmp_path) -> None:
    """Issue #5693: Creating new directories should still work after the fix."""
    # Path that doesn't exist yet
    db_path = tmp_path / "new" / "nested" / "todo.json"

    storage = TodoStorage(str(db_path))

    # Should succeed and create directories
    storage.save([])
    assert db_path.exists()
    assert db_path.parent.is_dir()


def test_symlink_to_file_in_parent_path_blocked(tmp_path) -> None:
    """Issue #5693: Symlink pointing to a file in the parent path should be blocked.

    This is the specific attack scenario mentioned in the issue:
    - Attacker creates symlink to a file in the parent path
    - Victim tries to save to a path that goes through that symlink
    - Without fix: symlink is followed, data could be written to unexpected location
    """
    # Create a regular file
    regular_file = tmp_path / "regular.txt"
    regular_file.write_text("content")

    # Create a symlink that looks like a directory name but points to the file
    fake_dir = tmp_path / "fake_directory"
    fake_dir.symlink_to(regular_file)

    # Verify symlink setup
    assert fake_dir.is_symlink()
    assert fake_dir.exists()  # exists() follows symlink
    assert not fake_dir.is_dir()  # Points to file, not directory

    # Attempt to save through the symlink path
    db_path = fake_dir / "db.json"
    storage = TodoStorage(str(db_path))

    # Should raise ValueError about the symlink/file conflict
    with pytest.raises(ValueError, match=r"(symlink|not a directory)"):
        storage.save([])

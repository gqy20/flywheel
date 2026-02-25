"""Regression tests for issue #5693: Symlink TOCTOU race condition in _ensure_parent_directory.

Issue: _ensure_parent_directory() uses exists() and is_dir() which follow symlinks,
allowing TOCTOU race condition attacks.

These tests verify that:
1. Symlinks in parent paths are properly detected and rejected
2. The function uses lstat()-style checks that don't follow symlinks
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_fails_when_parent_is_symlink_to_file(tmp_path) -> None:
    """Issue #5693: Should fail when parent path component is a symlink to a file.

    Security: An attacker could create a symlink from a path we check to a file
    they control, then after our check passes, change the symlink target.
    Using exists() follows the symlink and checks the target, which is vulnerable.
    """
    # Create a regular file
    target_file = tmp_path / "target_file.txt"
    target_file.write_text("I am a file")

    # Create a symlink pointing to the file
    symlink_path = tmp_path / "symlink_to_file"
    symlink_path.symlink_to(target_file)

    # Try to create database inside what appears to be a directory
    # but is actually a symlink to a file
    db_path = symlink_path / "data.json"

    storage = TodoStorage(str(db_path))

    # Should fail because parent is a symlink
    with pytest.raises(ValueError, match=r"(symbolic link|symlink)"):
        storage.save([])


def test_storage_fails_when_parent_is_symlink_to_directory(tmp_path) -> None:
    """Issue #5693: Should fail when parent path component is a symlink to a directory.

    Even if the symlink points to a valid directory, we should reject it to prevent
    TOCTOU race conditions where the symlink target could change between check and use.
    """
    # Create a directory
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()

    # Create a symlink pointing to the directory
    symlink_path = tmp_path / "symlink_to_dir"
    symlink_path.symlink_to(target_dir)

    # Try to create database inside the symlinked path
    db_path = symlink_path / "data.json"

    storage = TodoStorage(str(db_path))

    # Should fail because parent path contains a symlink
    with pytest.raises(ValueError, match=r"(symbolic link|symlink)"):
        storage.save([])


def test_storage_fails_when_grandparent_is_symlink(tmp_path) -> None:
    """Issue #5693: Should detect symlinks anywhere in the parent path chain."""
    # Create a directory
    target_dir = tmp_path / "real_directory"
    target_dir.mkdir()

    # Create a symlink to the directory
    symlink_path = tmp_path / "symlink_directory"
    symlink_path.symlink_to(target_dir)

    # Try to create database at a path that traverses through the symlink
    db_path = symlink_path / "subdir" / "data.json"

    storage = TodoStorage(str(db_path))

    # Should fail because grandparent is a symlink
    with pytest.raises(ValueError, match=r"(symbolic link|symlink)"):
        storage.save([])


def test_storage_succeeds_with_normal_directory_structure(tmp_path) -> None:
    """Issue #5693: Normal directory creation should still work after the fix."""
    # Create a nested directory structure that doesn't exist yet
    db_path = tmp_path / "a" / "b" / "c" / "data.json"

    storage = TodoStorage(str(db_path))

    # Should succeed without errors
    storage.save([])

    # Verify the file was created
    assert db_path.exists()
    assert db_path.parent.is_dir()


def test_lexists_used_instead_of_exists(tmp_path, monkeypatch) -> None:
    """Issue #5693: Verify that the implementation uses lexists() style checks.

    This test ensures the fix uses lstat-style operations that don't follow symlinks.
    We verify by checking that a broken symlink is detected and rejected.
    """
    # Create a symlink to a non-existent target (dangling symlink)
    dangling_symlink = tmp_path / "dangling_link"
    dangling_symlink.symlink_to(tmp_path / "nonexistent_target")

    # Verify it's a dangling symlink
    assert dangling_symlink.is_symlink()
    assert not dangling_symlink.exists()  # exists() follows symlink, returns False

    # Try to use this dangling symlink as a parent directory
    db_path = dangling_symlink / "data.json"

    storage = TodoStorage(str(db_path))

    # Should fail because parent is a symlink (even though target doesn't exist)
    # Using exists() would return False (symlink target doesn't exist)
    # Using lexists() would return True (symlink itself exists)
    # We want the behavior to detect the symlink and reject it
    with pytest.raises(ValueError, match=r"(symbolic link|symlink)"):
        storage.save([])

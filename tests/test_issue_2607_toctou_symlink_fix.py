"""Regression tests for issue #2607: TOCTOU symlink vulnerability in _ensure_parent_directory.

Issue: The exists() check at line 43 and mkdir() at line 45 have a TOCTOU race condition.
An attacker could create a symlink between the exists() check and mkdir() call,
causing mkdir() to follow the symlink and create a directory in an unintended location.

Additionally, the validation loop at lines 35-40 doesn't check for symlinks, allowing
symlinks to be used as parent paths silently.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_rejects_symlink_to_directory(tmp_path) -> None:
    """Issue #2607: Should reject parent path that is a symlink to a directory.

    Before fix: Symlink is followed silently, allowing potential directory confusion attacks
    After fix: Should fail with clear error about symlink rejection

    This is the main vulnerability - an attacker could replace a legitimate directory
    with a symlink pointing elsewhere, and the code would silently follow it.
    """
    # Create a target directory where attacker wants data to go
    target_dir = tmp_path / "attacker_controlled"
    target_dir.mkdir()

    # Create a symlink that will replace the expected parent directory
    symlink_path = tmp_path / "expected_parent"
    symlink_path.symlink_to(target_dir)

    # Try to use the symlinked path as parent
    db_path = symlink_path / "todo.json"

    # Should fail because parent is a symlink
    with pytest.raises(ValueError, match=r"symlink"):
        _ensure_parent_directory(db_path)


def test_ensure_parent_rejects_nested_symlink_in_path(tmp_path) -> None:
    """Issue #2607: Should reject when any parent component is a symlink.

    Before fix: Only checks if path is a file, doesn't check for symlinks
    After fix: Should detect and reject symlinks anywhere in the parent chain
    """
    # Create a legitimate base directory
    base_dir = tmp_path / "base"
    base_dir.mkdir()

    # Create a target directory for attack
    attack_target = tmp_path / "attack_target"
    attack_target.mkdir()

    # Create a symlink in the middle of the path
    symlink_component = base_dir / "legitimate_name"
    symlink_component.symlink_to(attack_target)

    # Try to create database through the symlinked path
    db_path = symlink_component / "todo.json"

    # Should fail because a parent component is a symlink
    with pytest.raises(ValueError, match=r"symlink"):
        _ensure_parent_directory(db_path)


def test_mkdir_race_condition_with_dangling_symlink(tmp_path) -> None:
    """Issue #2607: Dangling symlink between exists() and mkdir() should be detected.

    Before fix: exists() returns False for dangling symlinks, mkdir() fails with FileExistsError
                 but error message doesn't clearly indicate symlink attack
    After fix: Should detect dangling symlink with clear error message

    This is actually already handled by exist_ok=False - the test verifies the
    fix doesn't break this behavior while improving the error message.
    """
    # Create a dangling symlink (target doesn't exist)
    dangling_target = tmp_path / "does_not_exist"
    symlink_path = tmp_path / "parent_symlink"
    symlink_path.symlink_to(dangling_target)

    db_path = symlink_path / "todo.json"

    # Should fail with clear error
    # FileExistsError is raised by mkdir with exist_ok=False when symlink exists
    with pytest.raises((OSError, ValueError), match=r"(symlink|exists|directory)"):
        _ensure_parent_directory(db_path)


def test_storage_save_with_symlink_parent(tmp_path) -> None:
    """Issue #2607: TodoStorage.save() should reject symlink parent.

    Before fix: save() follows symlink and writes to attacker-controlled location
    After fix: Should fail with clear error about symlink rejection
    """
    # Create a target directory
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Create a symlink parent
    symlink_parent = tmp_path / "symlink"
    symlink_parent.symlink_to(target_dir)

    # Create storage that would save through the symlink
    db_path = symlink_parent / "todo.json"
    storage = TodoStorage(str(db_path))

    todos = [Todo(id=1, text="test todo")]

    # Should fail with clear error about symlink
    with pytest.raises(ValueError, match=r"symlink"):
        storage.save(todos)


def test_ensure_parent_rejects_symlink_to_file(tmp_path) -> None:
    """Issue #2607: Symlink pointing to a file should be rejected.

    This is the existing file-as-directory confusion, but via symlink.
    """
    # Create a file
    target_file = tmp_path / "target_file.txt"
    target_file.write_text("I am a file")

    # Create a symlink pointing to the file
    symlink_path = tmp_path / "symlink_to_file"
    symlink_path.symlink_to(target_file)

    # Try to use the symlink as a parent directory
    db_path = symlink_path / "subdir" / "todo.json"

    # Should fail - cannot use a file (even via symlink) as directory
    # The symlink check should catch this before we even check if it's a file
    with pytest.raises(ValueError, match=r"symlink"):
        _ensure_parent_directory(db_path)


def test_normal_directory_creation_still_works(tmp_path) -> None:
    """Issue #2607: Normal directory creation should still work after fix."""
    # This is a sanity check - normal operations should not be affected
    db_path = tmp_path / "normal" / "nested" / "path" / "todo.json"

    # Should succeed
    _ensure_parent_directory(db_path)

    # Verify parent was created
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()
    assert not db_path.parent.is_symlink()


def test_existing_directory_still_works(tmp_path) -> None:
    """Issue #2607: Existing directory should still work after fix."""
    # Pre-create parent directory
    parent_dir = tmp_path / "existing_dir"
    parent_dir.mkdir()

    db_path = parent_dir / "todo.json"

    # Should succeed
    _ensure_parent_directory(db_path)

    assert db_path.parent.exists()
    assert db_path.parent == parent_dir

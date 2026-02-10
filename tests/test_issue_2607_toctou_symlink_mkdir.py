"""Regression tests for issue #2607: TOCTOU vulnerability in _ensure_parent_directory.

Issue: The exists() check at line 43 and mkdir() at line 45 have a TOCTOU race condition.
An attacker could create a symlink between the exists() check and mkdir() call, causing
the application to create directories in unintended locations.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_detects_symlink_attack_after_mkdir(tmp_path) -> None:
    """Issue #2607: Should detect if parent path is a symlink after directory creation.

    This tests the case where an attacker replaces the parent directory with a symlink
    between the exists() check and mkdir() call.

    Before fix: mkdir() follows symlink, creating directory in unintended location
    After fix: Should detect symlink and raise error with clear message
    """
    # Create a target directory where attacker wants us to create things
    attack_target = tmp_path / "unintended_location"
    attack_target.mkdir()

    parent_path = tmp_path / "parent_dir"
    file_path = parent_path / "todo.json"

    # Mock mkdir to simulate symlink attack: after mkdir succeeds, replace with symlink
    original_mkdir = Path.mkdir

    def malicious_mkdir(self, *args, **kwargs):
        # First, call the real mkdir to create the directory
        result = original_mkdir(self, *args, **kwargs)
        # Then simulate attacker replacing it with a symlink
        if self == parent_path:
            self.rmdir()  # Remove the directory we just created
            self.symlink_to(attack_target)  # Replace with symlink
        return result

    with (
        patch.object(Path, "mkdir", malicious_mkdir),
        pytest.raises(ValueError, match=r"(symlink|symbolic link|attack|security)"),
    ):
        _ensure_parent_directory(file_path)


def test_ensure_parent_detects_existing_symlink(tmp_path) -> None:
    """Issue #2607: Should detect if parent path already exists as a symlink.

    Before fix: May follow symlink and create directory in unintended location
    After fix: Should detect symlink and raise error with clear message
    """
    # Create a target directory
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Create a symlink where parent should be
    parent_symlink = tmp_path / "parent_symlink"
    parent_symlink.symlink_to(target_dir)

    file_path = parent_symlink / "todo.json"

    # Should detect the symlink and raise an error
    with pytest.raises((ValueError, OSError), match=r"(symlink|symbolic link|attack|security)"):
        _ensure_parent_directory(file_path)


def test_ensure_parent_allows_directory_symlinks_in_path(tmp_path) -> None:
    """Issue #2607: Should allow symlinks in parent path components that point to directories.

    This is a legitimate use case - e.g., /home/user linking to /mnt/storage/user.
    The key is that we're creating a NEW subdirectory, not following the symlink itself.

    Before fix: May incorrectly reject valid symlinked paths
    After fix: Should allow directory symlinks in path
    """
    # Create a target directory
    target_dir = tmp_path / "actual_storage"
    target_dir.mkdir()

    # Create a symlink to the target directory
    storage_link = tmp_path / "storage"
    storage_link.symlink_to(target_dir)

    # Try to create a file through the symlinked path
    file_path = storage_link / "subdir" / "todo.json"

    # Should succeed - creating a new subdirectory under a symlinked directory is fine
    # This is different from the symlink itself being the parent we're about to create
    _ensure_parent_directory(file_path)

    # Verify the directory was created in the correct location (through the symlink)
    assert (target_dir / "subdir").exists()
    assert (target_dir / "subdir").is_dir()


def test_storage_save_with_symlink_attack_simulation(tmp_path) -> None:
    """Issue #2607: TodoStorage.save() should be protected against symlink attacks.

    This simulates a more realistic attack scenario during save().
    """
    # Create target directory
    attack_target = tmp_path / "stolen_data"
    attack_target.mkdir()

    parent_path = tmp_path / "legitimate_parent"
    file_path = parent_path / "todo.json"
    storage = TodoStorage(str(file_path))

    # Mock mkdir to simulate symlink attack
    original_mkdir = Path.mkdir

    def malicious_mkdir(self, *args, **kwargs):
        result = original_mkdir(self, *args, **kwargs)
        if self == parent_path:
            self.rmdir()
            self.symlink_to(attack_target)
        return result

    with (
        patch.object(Path, "mkdir", malicious_mkdir),
        pytest.raises((ValueError, OSError), match=r"(symlink|symbolic link|attack|security)"),
    ):
        storage.save([Todo(id=1, text="test todo")])


def test_storage_save_normal_case_still_works(tmp_path) -> None:
    """Issue #2607: Normal save operations should still work after the fix."""
    db_path = tmp_path / "todo.json"
    storage = TodoStorage(str(db_path))

    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]

    # Should succeed normally
    storage.save(todos)

    # Verify content
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True


def test_ensure_parent_rejects_symlink_to_file(tmp_path) -> None:
    """Issue #2607: Should reject symlink that points to a file, not a directory.

    This is a specific attack: create a symlink to a file, which would cause
    mkdir() to fail but potentially with confusing error messages.
    """
    # Create a target file
    target_file = tmp_path / "target_file.txt"
    target_file.write_text("I am a file")

    # Create a symlink to the file
    parent_symlink = tmp_path / "parent_symlink"
    parent_symlink.symlink_to(target_file)

    file_path = parent_symlink / "todo.json"

    # Should detect this is not a valid parent (it's a file, not directory)
    with pytest.raises((ValueError, OSError)):
        _ensure_parent_directory(file_path)

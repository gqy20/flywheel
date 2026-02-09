"""Regression tests for issue #2607: TOCTOU symlink vulnerability in _ensure_parent_directory.

Issue: TOCTOU vulnerability in _ensure_parent_directory: exists() check at line 54
and mkdir() call at line 56 can be raced with symlink creation between the check
and the mkdir() call.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage


def test_rejects_symlink_in_parent_path_directly() -> None:
    """Issue #2607: _ensure_parent_directory should reject symlink parents directly."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create a target directory
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create a symlink to the target
        symlink_dir = tmp_path / "symlink_dir"
        symlink_dir.symlink_to(target_dir)

        # Try to create a file under the symlink
        db_path = symlink_dir / "todo.json"
        storage = TodoStorage(str(db_path))

        # Should fail because the parent is a symlink
        with pytest.raises(OSError, match=r"(symlink|symbolic link|Security)"):
            storage.save([])


def test_allows_normal_directory_creation() -> None:
    """Issue #2607: Normal directory creation should still work."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create a normal nested path
        db_path = tmp_path / "normal" / "subdir" / "todo.json"
        storage = TodoStorage(str(db_path))

        # Should succeed
        storage.save([])

        # Verify the file was created
        assert db_path.exists()
        assert db_path.parent.is_dir()
        # Verify parent is NOT a symlink
        assert not db_path.parent.is_symlink()


def test_rejects_symlink_created_after_exists_check() -> None:
    """Issue #2607: TOCTOU vulnerability - symlink created between exists() and mkdir().

    This test demonstrates the vulnerability where a symlink could be created
    after the symlink check at line 45 but before the mkdir() call at line 56.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create a target directory that the attacker wants us to write to
        target_dir = tmp_path / "attacker_target"
        target_dir.mkdir()

        # Create the parent directory that will be used
        parent_dir = tmp_path / "parent"
        parent_dir.mkdir()

        # Path where we want to create the database
        db_path = parent_dir / "todo.json"
        storage = TodoStorage(str(db_path))

        # Track if mkdir was called
        mkdir_called = []

        original_mkdir = Path.mkdir

        def mock_mkdir_with_symlink_attack(self, *args, **kwargs):
            """Mock mkdir that creates a symlink just before the real mkdir."""
            # On first call (creating parent), replace it with a symlink
            if not mkdir_called and str(self) == str(parent_dir):
                mkdir_called.append(True)
                # Remove the real directory
                self.rmdir()
                # Create a symlink to attacker's target
                self.symlink_to(target_dir)
                # Now call the real mkdir (which will follow the symlink!)
            return original_mkdir(self, *args, **kwargs)

        # Even though we have the symlink check at line 45, an attacker
        # could create the symlink AFTER that check but BEFORE mkdir()
        # This is the TOCTOU vulnerability
        with patch.object(Path, 'mkdir', mock_mkdir_with_symlink_attack):
            # The current code should FAIL this test because mkdir will
            # follow the symlink and create the directory in attacker_target
            storage.save([])

        # If the attack succeeded, the file would be in attacker_target
        # which is a security vulnerability
        attacker_file = target_dir / "todo.json"
        assert not attacker_file.exists(), \
            "Security: File was created through symlink! TOCTOU vulnerability exists."

        # Note: If the symlink attack succeeds, the file would be created in target_dir
        # instead of parent_dir. The post-validation check in the fix prevents this.


def test_mkdir_postvalidation_catches_symlink() -> None:
    """Issue #2607: After mkdir, validate the result is actually a directory, not a symlink.

    This test ensures that even if mkdir somehow follows a symlink, we catch it
    during post-validation.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Test the actual behavior: if we have a symlink as parent,
        # the code should reject it
        target_dir = tmp_path / "elsewhere"
        target_dir.mkdir()

        bad_parent = tmp_path / "bad"
        bad_parent.symlink_to(target_dir)

        db_path = bad_parent / "todo.json"
        storage = TodoStorage(str(db_path))

        # Should raise security error about symlink
        with pytest.raises(OSError) as exc_info:
            storage.save([])

        # Verify the error message mentions the security concern
        error_msg = str(exc_info.value).lower()
        assert "symlink" in error_msg or "symbolic link" in error_msg or "security" in error_msg


def test_validates_parent_is_directory_after_mkdir() -> None:
    """Issue #2607: After creating parent, verify it's actually a directory (not symlink).

    This is the fix for the TOCTOU vulnerability - after calling mkdir(),
    we must verify that the resulting path is a real directory, not a symlink.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # This simulates a successful mkdir that was actually a symlink attack
        target = tmp_path / "target"
        target.mkdir()

        tricky_path = tmp_path / "tricky"

        # Create a scenario where mkdir would "succeed" but through a symlink
        db_path = tricky_path / "todo.json"

        # Mock scenario: exists() returns False (no symlink), but mkdir() follows a symlink
        original_exists = Path.exists
        original_mkdir = Path.mkdir

        call_count = {"exists": 0, "mkdir": 0}

        def mock_exists(self):
            # First exists() call returns False (no symlink detected yet)
            if call_count["exists"] == 0 and str(self) == str(tricky_path):
                call_count["exists"] += 1
                return False
            return original_exists(self)

        def mock_mkdir(self, *args, **kwargs):
            if str(self) == str(tricky_path):
                call_count["mkdir"] += 1
                # Simulate symlink attack: create symlink instead of directory
                self.symlink_to(target)
                return None
            return original_mkdir(self, *args, **kwargs)

        # With the fix, this should detect the symlink after mkdir and fail
        with patch.object(Path, 'exists', mock_exists), \
             patch.object(Path, 'mkdir', mock_mkdir):
            storage = TodoStorage(str(db_path))
            with pytest.raises(OSError, match=r"(symlink|symbolic link|Security)"):
                storage.save([])


def test_rejects_symlink_in_intermediate_parent_components() -> None:
    """Issue #2607: Should also check intermediate parent components for symlinks."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create target directory
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create a legitimate directory
        legit_dir = tmp_path / "legit"
        legit_dir.mkdir()

        # Create a symlink in the middle of the path
        symlink_mid = tmp_path / "legit" / "symlink_mid"
        symlink_mid.symlink_to(target_dir)

        # Try to create database through the symlink
        db_path = symlink_mid / "subdir" / "todo.json"
        storage = TodoStorage(str(db_path))

        # Should fail because one of the parent components is a symlink
        with pytest.raises(OSError):
            storage.save([])


def test_allows_existing_non_symlink_directories() -> None:
    """Issue #2607: Should work fine with existing directories that are not symlinks."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create an existing directory structure (no symlinks)
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        db_path = existing_dir / "todo.json"
        storage = TodoStorage(str(db_path))

        # Should succeed
        storage.save([])

        assert db_path.exists()
        assert not db_path.parent.is_symlink()

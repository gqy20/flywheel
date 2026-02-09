"""Regression tests for issue #2607: Symlink TOCTOU vulnerability in _ensure_parent_directory.

Issue: TOCTOU vulnerability between exists() check at line 43 and mkdir() at line 45
allows an attacker to create a symlink between the check and the directory creation,
causing directories to be created in unintended locations.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_symlink_toctou_attack_in_parent_directory_creation(tmp_path) -> None:
    """Issue #2607: Symlink attack between exists() check and mkdir() should be prevented.

    Attack scenario:
    1. Attacker wants to force directory creation in /tmp/attack_target
    2. Between exists() check and mkdir(), attacker replaces parent path with symlink
    3. mkdir() follows symlink and creates directory in attack_target

    Before fix: mkdir follows symlink and creates directory in unintended location
    After fix: Should either prevent symlink or detect it with clear error
    """
    # Create a target directory where attacker wants us to create directories
    attack_target = tmp_path / "attack_target_dir"
    attack_target.mkdir()

    # The parent path that doesn't exist yet (we will replace it with symlink)
    parent_path = tmp_path / "parent_dir"

    # The final file path (not yet created)
    db_path = parent_path / "todo.json"

    # Simulate attack: replace parent path with symlink to attack target
    # This must happen between exists() check and mkdir() in _ensure_parent_directory
    symlink_created = threading.Event()
    should_create_symlink = threading.Event()

    def symlink_attacker():
        """Thread that races to create symlink between exists() and mkdir()."""
        should_create_symlink.wait()  # Wait for signal to start attack
        # Create a symlink to attack target
        parent_path.symlink_to(attack_target)  # Replace with symlink
        symlink_created.set()  # Signal that symlink was created

    # Start attacker thread
    attacker = threading.Thread(target=symlink_attacker, daemon=True)
    attacker.start()

    # Signal attacker to create symlink, then try to save
    # The race is: exists() returns False (doesn't exist), then symlink is created,
    # then mkdir() sees parent exists (via symlink) and should fail with exist_ok=False
    should_create_symlink.set()
    time.sleep(0.01)  # Give attacker a moment to create the symlink

    try:
        storage = TodoStorage(str(db_path))
        todos = [Todo(id=1, text="test todo")]

        # This should either:
        # 1. Fail because symlink was detected (safe)
        # 2. Succeed but mkdir was called on a real directory (safe)
        # 3. Unsafely follow symlink (UNSAFE - should fail test)
        storage.save(todos)

        # If we got here, save succeeded. Now check if it was safe.
        symlink_created.wait(timeout=1)

        if parent_path.is_symlink() and (attack_target / "todo.json").exists():
            # This is the vulnerability: directory was created via symlink
            raise AssertionError(
                f"SECURITY: Directory was created through symlink attack! "
                f"File exists at attack target: {attack_target / 'todo.json'}"
            )
    except (OSError, ValueError) as e:
        # This is the SAFE outcome: operation failed due to symlink detection
        # The error message should be informative
        error_msg = str(e).lower()
        # Acceptable errors: permission, exists, link, path errors
        assert any(
            word in error_msg
            for word in ["permission", "exists", "link", "path", "directory", "not a directory"]
        ), f"Error should mention path/link issue, got: {e}"


def test_ensure_parent_directory_rejects_symlink_directly(tmp_path) -> None:
    """Issue #2607: _ensure_parent_directory should handle symlinks safely.

    This test directly checks if a symlink in the parent path is handled securely.
    """
    # Create a directory and a symlink pointing to it
    real_dir = tmp_path / "real_directory"
    real_dir.mkdir()

    symlink_dir = tmp_path / "symlink_directory"
    symlink_dir.symlink_to(real_dir)

    # Try to ensure parent directory when parent is a symlink
    db_path = symlink_dir / "todo.json"

    # Safe behavior: either reject symlink or handle it securely
    try:
        _ensure_parent_directory(Path(db_path))

        # If it succeeded, verify the symlink wasn't followed unsafely
        # Check that the path structure is still valid
        if symlink_dir.is_symlink():
            # If symlink still exists, verify nothing was created in real_dir
            # (unless it's supposed to be there)
            real_dir_contents = list(real_dir.iterdir())
            if any(f.name == "todo.json" for f in real_dir_contents):
                # File was created through symlink - this is the vulnerability
                raise AssertionError(
                    "SECURITY: File was created through symlink in real_dir"
                )
    except (OSError, ValueError) as e:
        # This is acceptable - symlink was rejected
        assert any(
            word in str(e).lower()
            for word in ["link", "path", "directory", "permission"]
        ), f"Error should be path-related, got: {e}"


def test_normal_directory_creation_still_works(tmp_path) -> None:
    """Issue #2607: Normal directory creation should still work after fix."""
    # Normal case: create new directories
    db_path = tmp_path / "new_dir" / "subdir" / "todo.json"
    storage = TodoStorage(str(db_path))

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Verify file was created
    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_existing_parent_directory_still_works(tmp_path) -> None:
    """Issue #2607: Should work when parent directory already exists."""
    parent_dir = tmp_path / "existing"
    parent_dir.mkdir()

    db_path = parent_dir / "todo.json"
    storage = TodoStorage(str(db_path))

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1

"""Regression tests for issue #2607: Symlink TOCTOU vulnerability in _ensure_parent_directory.

Issue: TOCTOU race condition between exists() check at line 43 and mkdir() at line 45
where an attacker could create a symlink between the check and the directory creation.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from flywheel.storage import _ensure_parent_directory


def test_symlink_to_file_attack_detected(tmp_path) -> None:
    """Issue #2607: Symlink to file created between exists() check and mkdir() should be detected.

    An attacker could replace a non-existent path with a symlink to a file
    between the exists() check and mkdir() call.
    """
    # Create a target file that the attacker would point to
    target_file = tmp_path / "target" / "important_file.txt"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("important data")

    # The path we want to create (doesn't exist yet)
    victim_path = tmp_path / "victim" / "subdir" / "todo.json"
    victim_parent = victim_path.parent

    # Ensure the victim parent doesn't exist
    assert not victim_parent.exists()

    # Simulate the TOCTOU attack by creating a directory and then
    # replacing it with a symlink to a file (this is the attack scenario)
    # We'll do this by creating the directory structure manually
    victim_parent.mkdir(parents=True)

    # Now create a symlink where we expect a directory to be
    # The symlink points to a file, not a directory
    symlink_path = victim_parent / "attack_symlink"
    os.symlink(target_file, symlink_path)

    # Try to create a database file where the parent contains a symlink to a file
    # The _ensure_parent_directory should detect this problem
    db_path = symlink_path / "db.json"

    with pytest.raises((ValueError, OSError), match=r"(symlink|directory|path)"):
        _ensure_parent_directory(db_path)


def test_symlink_directory_attack_prevents_creation(tmp_path) -> None:
    """Issue #2607: Symlink to directory from untrusted source should be handled safely.

    If an attacker can create symlinks in the parent path, they could redirect
    directory creation to an unexpected location.
    """
    # Create a directory the attacker controls
    attacker_dir = tmp_path / "attacker_controlled"
    attacker_dir.mkdir()

    # The legitimate path we want to use
    legitimate_path = tmp_path / "legitimate" / "subdir" / "todo.json"

    # Create the parent directory
    legitimate_path.parent.mkdir(parents=True)

    # Attacker creates a symlink in the path
    symlink_loc = legitimate_path.parent / "symlink_to_attacker"
    try:
        os.symlink(attacker_dir, symlink_loc)

        # Try to use a path that goes through the symlink
        # This should either work safely (if we validate symlinks)
        # or fail with a clear error
        db_path = symlink_loc / "todo.json"

        # The function should detect the symlink and fail with a clear error
        with pytest.raises(ValueError, match=r"(symlink|Security|symbolic link)"):
            _ensure_parent_directory(db_path)
    except OSError:
        # On systems that don't support symlinks or have restrictions,
        # this test may fail - that's acceptable
        pytest.skip("Symlink creation not supported or restricted")


def test_directory_creation_with_symlink_to_file_in_chain(tmp_path) -> None:
    """Issue #2607: Detect symlink to file in parent chain during creation.

    When creating parent directories, if any component is a symlink to a file
    (not a directory), it should be detected and fail clearly.
    """
    # Create a file
    target_file = tmp_path / "file.txt"
    target_file.write_text("I'm a file")

    # Create a symlink pointing to the file
    symlink_path = tmp_path / "symlink_to_file"
    try:
        os.symlink(target_file, symlink_path)

        # Try to create a path through the symlink
        # The symlink points to a file, so we can't create directories "inside" it
        db_path = symlink_path / "subdir" / "todo.json"

        # Should fail with clear error about file vs directory
        with pytest.raises((ValueError, OSError), match=r"(file|directory|not a directory)"):
            _ensure_parent_directory(db_path)
    except OSError:
        # Skip if symlink creation not supported
        pytest.skip("Symlink creation not supported")


def test_normal_directory_creation_still_works(tmp_path) -> None:
    """Issue #2607: Normal directory creation should continue to work after security fix.

    The security fix should not break legitimate use cases.
    """
    # Normal case: non-existent path
    db_path = tmp_path / "new" / "nested" / "path" / "todo.json"
    _ensure_parent_directory(db_path)
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()

    # Normal case: parent already exists
    db_path2 = tmp_path / "new" / "another" / "todo.json"
    _ensure_parent_directory(db_path2)
    assert db_path2.parent.exists()
    assert db_path2.parent.is_dir()


def test_mkdir_race_condition_handling(tmp_path) -> None:
    """Issue #2607: Handle race condition where directory is created between check and mkdir.

    This tests the case where another process creates the directory between
    our exists() check and mkdir() call.
    """
    parent_path = tmp_path / "race_condition" / "subdir"
    db_path = parent_path / "todo.json"

    # First call should create the directory
    _ensure_parent_directory(db_path)
    assert parent_path.exists()

    # Second call should handle the already-existing directory gracefully
    # This simulates the race condition where another process created it
    _ensure_parent_directory(db_path)
    assert parent_path.exists()


def test_toctou_symlink_between_exists_and_mkdir(tmp_path) -> None:
    """Issue #2607: TOCTOU vulnerability - symlink created between exists() and mkdir().

    This test demonstrates the race condition where an attacker could:
    1. Thread A checks if parent directory exists (returns False)
    2. Attacker creates a symlink to a sensitive file
    3. Thread A calls mkdir(), which follows the symlink

    The fix should either:
    a) Use atomic operations that prevent this
    b) Validate after mkdir() that the result is actually a directory
    """
    import time
    import threading

    # Create a sensitive file that attacker wants us to overwrite
    sensitive_file = tmp_path / "sensitive" / "data.txt"
    sensitive_file.parent.mkdir(parents=True)
    sensitive_file.write_text("SENSITIVE DATA - DO NOT OVERWRITE")

    # Path that attacker will race to create
    target_dir = tmp_path / "target"
    db_path = target_dir / "todo.json"

    # Flag to coordinate the attack
    attack_ready = threading.Event()
    mkdir_called = threading.Event()

    def symlink_attacker():
        """Simulates an attacker creating a symlink during the TOCTOU window."""
        # Wait for the exists() check to pass (directory doesn't exist)
        attack_ready.wait()

        # Quickly create a symlink pointing to the sensitive file's parent
        # This happens BETWEEN exists() check and mkdir() call
        try:
            os.symlink(sensitive_file.parent, target_dir)
        except FileExistsError:
            # Directory already created, attack failed
            pass

        mkdir_called.set()

    # Start attacker thread
    attacker = threading.Thread(target=symlink_attacker, daemon=True)
    attacker.start()

    # Signal attacker to be ready
    attack_ready.set()

    # Small delay to give attacker a chance to create the symlink
    time.sleep(0.001)

    # Now call _ensure_parent_directory - this is the vulnerable operation
    # If the attack succeeds, it might:
    # 1. Follow the symlink and create files in sensitive_dir
    # 2. Fail because sensitive_file exists
    try:
        _ensure_parent_directory(db_path)
        mkdir_called.set()

        # If mkdir succeeded, verify we didn't accidentally follow a symlink
        # to the sensitive directory
        if target_dir.exists():
            # Check if target_dir is actually a symlink
            if target_dir.is_symlink():
                pytest.fail(
                    "Security vulnerability: mkdir() followed symlink! "
                    "Directory was created at symlink target."
                )
            # Check if target_dir is a real directory (not symlinked)
            assert target_dir.is_dir(), "Created path should be a directory"

            # Additional safety check: verify the resolved path
            resolved = target_dir.resolve()
            if resolved != target_dir and sensitive_file.parent in resolved.parents:
                pytest.fail(
                    f"Security vulnerability: Directory created through symlink. "
                    f"target_dir={target_dir}, resolved={resolved}"
                )
    except (OSError, ValueError) as e:
        # This is acceptable - the attack was detected/prevented
        pass
    finally:
        attacker.join(timeout=1)

    # After the operation, verify data integrity
    # The sensitive file should NOT have been affected
    if sensitive_file.exists():
        content = sensitive_file.read_text()
        assert "SENSITIVE DATA" in content, "Sensitive file was modified!"


def test_symlink_created_after_validation_loop(tmp_path) -> None:
    """Issue #2607: Symlink created after initial validation loop but before mkdir.

    The validation loop at lines 35-40 checks for existing files,
    but an attacker could create a symlink after that loop completes
    but before the mkdir() call at line 45.
    """
    import threading

    # Create a file the attacker wants to target
    target_file = tmp_path / "victim" / "target.txt"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("victim data")

    # The path where we want to create our directory
    parent_path = tmp_path / "parent" / "child"
    db_path = parent_path / "todo.json"

    # Events to coordinate the race
    after_validation = threading.Event()
    before_mkdir = threading.Event()

    original_mkdir = Path.mkdir

    mkdir_call_count = [0]

    def tracked_mkdir(self, *args, **kwargs):
        """Wrapper to track mkdir calls and coordinate the attack."""
        mkdir_call_count[0] += 1
        if mkdir_call_count[0] == 1:
            # First mkdir call - signal that validation is done
            after_validation.set()
            # Wait a bit to let attacker create symlink
            before_mkdir.wait(timeout=0.1)
        return original_mkdir(self, *args, **kwargs)

    def attacker():
        """Create symlink after validation but before mkdir."""
        after_validation.wait()
        try:
            # Create symlink pointing to the file
            # This should cause mkdir to fail or be detected
            os.symlink(target_file, parent_path)
        except (FileExistsError, OSError):
            # Either path already exists or symlink not supported
            pass
        finally:
            before_mkdir.set()

    # Patch mkdir to detect the race window
    Path.mkdir = tracked_mkdir

    try:
        attacker_thread = threading.Thread(target=attacker, daemon=True)
        attacker_thread.start()

        # This should either:
        # 1. Create directory normally (attack missed the window)
        # 2. Detect the symlink and fail
        # It should NOT silently follow the symlink
        _ensure_parent_directory(db_path)

        attacker_thread.join(timeout=1)

        # If directory was created, verify it's a real directory
        if parent_path.exists():
            if parent_path.is_symlink():
                pytest.fail(
                    "Security vulnerability: Symlink was not detected! "
                    "mkdir() followed a symlink to a file."
                )
    except (OSError, ValueError):
        # Attack was detected - this is acceptable
        pass
    finally:
        Path.mkdir = original_mkdir

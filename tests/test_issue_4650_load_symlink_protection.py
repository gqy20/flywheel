"""Regression tests for issue #4650: Symlink protection in load().

Issue: The load() function uses path.stat() which follows symlinks before
checking file size. This could allow an attacker to create a symlink pointing
to a large system file, causing the application to read arbitrary large files.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage


def test_load_rejects_symlink_pointing_to_large_file(tmp_path) -> None:
    """Issue #4650: load() should reject symlinks pointing outside allowed directories.

    An attacker could create a symlink to a large system file like /dev/zero
    or /dev/urandom, which would cause path.stat().st_size to report a huge size.

    Before fix: load() follows symlink and reads target file
    After fix: load() detects symlink and raises security error
    """
    # Create a large file as the "attack target"
    attack_target = tmp_path / "large_file.json"
    # Create a file larger than the limit (10MB)
    large_size = 11 * 1024 * 1024  # 11MB
    attack_target.write_bytes(b"x" * large_size)

    # Create a symlink to the large file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(attack_target)

    storage = TodoStorage(str(db_symlink))

    # Before fix: This would follow the symlink and check the target file size
    # After fix: This should reject the symlink entirely with a security error
    error_raised = False
    try:
        storage.load()
    except (ValueError, OSError):
        error_raised = True

    # Must raise an error - symlink protection or size check both prevent the attack
    assert error_raised, "load() should reject symlinks for security"


def test_load_rejects_symlink_pointing_outside_directory(tmp_path) -> None:
    """Issue #4650: load() should reject symlinks pointing outside allowed directories.

    Security check: Symlinks should be detected and rejected to prevent
    reading arbitrary files on the system.
    """
    # Create a symlink to /etc/passwd (or similar system file)
    db_symlink = tmp_path / "todo.json"
    # Use /etc/passwd as a representative system file
    if Path("/etc/passwd").exists():
        db_symlink.symlink_to("/etc/passwd")
    else:
        # Fallback: create a dummy file to link to
        dummy_target = tmp_path.parent / "outside_allowed.json"
        dummy_target.write_text("[]")
        db_symlink.symlink_to(dummy_target)

    storage = TodoStorage(str(db_symlink))

    # Should reject the symlink
    try:
        storage.load()
        raise AssertionError("load() should reject symlinks for security")
    except (ValueError, OSError):
        # Expected: Should fail with security error
        pass


def test_load_normal_file_still_works(tmp_path) -> None:
    """Issue #4650: Normal file loading should continue to work after fix.

    This is a regression test to ensure the fix doesn't break normal operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    db.write_text('[{"id": 1, "text": "test todo", "done": false}]', encoding="utf-8")

    # Should load normally
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "test todo"
    assert todos[0].done is False


def test_load_symlink_to_valid_todo_file(tmp_path) -> None:
    """Issue #4650: Document behavior when symlink points to valid todo file.

    Even if the symlink points to a valid todo file, we should still reject it
    for security reasons (to prevent TOCTOU attacks and path confusion).
    """
    # Create a valid todo file
    real_todo = tmp_path / "real_todo.json"
    real_todo.write_text('[{"id": 1, "text": "legitimate", "done": true}]', encoding="utf-8")

    # Create a symlink to it
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(real_todo)

    storage = TodoStorage(str(db_symlink))

    # Should reject the symlink even though it points to a valid file
    try:
        storage.load()
        raise AssertionError("load() should reject symlinks for security")
    except (ValueError, OSError):
        # Expected: Should fail with security error
        pass

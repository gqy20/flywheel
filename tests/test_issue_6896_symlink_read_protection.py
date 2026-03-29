"""Regression tests for issue #6896: Symlink attack protection in load().

Issue: The load() function follows symlinks allowing arbitrary file read
if an attacker can create a symlink at the db path.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_rejects_symlink_pointing_to_file(tmp_path) -> None:
    """Issue #6896: load() should reject when db path is a symlink.

    Before fix: load() follows symlink and reads target file content
    After fix: load() should detect symlink and raise ValueError
    """
    # Create a target file with sensitive content
    sensitive_file = tmp_path / "sensitive_data.json"
    sensitive_content = [{"id": 1, "text": "secret data", "done": False}]
    sensitive_file.write_text(json.dumps(sensitive_content), encoding="utf-8")

    # Create a symlink at the db path pointing to the sensitive file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(sensitive_file)

    storage = TodoStorage(str(db_symlink))

    # Before fix: load() would follow symlink and expose sensitive content
    # After fix: load() should reject the symlink with a clear error
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_rejects_symlink_pointing_to_directory(tmp_path) -> None:
    """Issue #6896: load() should reject when db path is a symlink to a directory."""
    # Create a directory
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()

    # Create a symlink pointing to the directory
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(target_dir)

    storage = TodoStorage(str(db_symlink))

    # Should reject symlink regardless of what it points to
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_succeeds_with_regular_file(tmp_path) -> None:
    """Issue #6896: load() should work normally with regular files (not symlinks)."""
    db = tmp_path / "todo.json"
    todos = [Todo(id=1, text="test todo")]
    storage = TodoStorage(str(db))
    storage.save(todos)

    # Should succeed with regular file
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_load_returns_empty_for_nonexistent_file(tmp_path) -> None:
    """Issue #6896: load() should return empty list for nonexistent file."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list, not raise error
    loaded = storage.load()
    assert loaded == []


def test_load_symlink_with_broken_target(tmp_path) -> None:
    """Issue #6896: load() should handle broken symlinks safely.

    A broken symlink (target doesn't exist) should still be rejected
    because it's a symlink, not because the target is missing.
    """
    # Create a symlink pointing to a non-existent file
    nonexistent = tmp_path / "does_not_exist.json"
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(nonexistent)

    storage = TodoStorage(str(db_symlink))

    # Should reject the symlink (not follow it and fail due to missing target)
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_symlink_cannot_expose_etc_passwd(tmp_path) -> None:
    """Issue #6896: load() should not allow reading arbitrary system files via symlink.

    This is the primary security test: an attacker creates a symlink
    to /etc/passwd or other sensitive system files.
    """
    # Skip if /etc/passwd doesn't exist (uncommon but possible)
    passwd_path = Path("/etc/passwd")
    if not passwd_path.exists():
        pytest.skip("/etc/passwd does not exist on this system")

    # Create a symlink to /etc/passwd
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(passwd_path)

    storage = TodoStorage(str(db_symlink))

    # Before fix: load() would read /etc/passwd content
    # After fix: load() should reject the symlink
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_error_message_is_clear(tmp_path) -> None:
    """Issue #6896: Error message should clearly indicate symlink issue."""
    # Create a target file
    target = tmp_path / "target.json"
    target.write_text("[]", encoding="utf-8")

    # Create symlink
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(target)

    storage = TodoStorage(str(db_symlink))

    try:
        storage.load()
        pytest.fail("Expected ValueError for symlink")
    except ValueError as e:
        error_msg = str(e).lower()
        # Error message should mention "symlink" and some indication of security
        assert "symlink" in error_msg, f"Error message should mention symlink: {e}"

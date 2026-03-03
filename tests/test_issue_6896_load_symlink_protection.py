"""Regression tests for issue #6896: Symlink attack protection in load().

Issue: load() follows symlinks allowing arbitrary file read if attacker can create
symlink at db path.

Security vulnerability: If an attacker can create a symlink at the database path
(e.g., replacing .todo.json with a symlink to /etc/passwd), load() will follow
the symlink and read arbitrary file content, potentially exposing sensitive data.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_symlink_pointing_to_file(tmp_path) -> None:
    """Issue #6896: load() should reject when db path is a symlink.

    Before fix: load() follows symlink and reads target file content
    After fix: load() should raise ValueError when path is a symlink
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a target file that attacker wants us to read
    attack_target = tmp_path / "sensitive_data.txt"
    attack_target.write_text("secret password: admin123")

    # Remove the db file and create a symlink pointing to attack target
    if db.exists():
        db.unlink()
    db.symlink_to(attack_target)

    # Verify the symlink was created correctly
    assert db.is_symlink(), "Test setup failed: db should be a symlink"

    # load() should reject the symlink and not read the sensitive file
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_rejects_symlink_pointing_to_valid_json(tmp_path) -> None:
    """Issue #6896: load() should reject symlinks even if target is valid JSON.

    This ensures attackers cannot inject todo items via symlink to another JSON file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a target JSON file with malicious todo items
    attack_target = tmp_path / "attack_payload.json"
    attack_payload = [{"id": 1, "text": "injected malicious todo", "done": False}]
    attack_target.write_text(json.dumps(attack_payload), encoding="utf-8")

    # Remove the db file and create a symlink pointing to attack target
    if db.exists():
        db.unlink()
    db.symlink_to(attack_target)

    # Verify the symlink was created correctly
    assert db.is_symlink(), "Test setup failed: db should be a symlink"

    # load() should reject the symlink, not load the malicious todos
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_works_with_regular_file(tmp_path) -> None:
    """Issue #6896: load() should still work with regular (non-symlink) files.

    This is a regression test to ensure the fix doesn't break normal operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a regular file with valid JSON
    valid_todos = [{"id": 1, "text": "normal todo", "done": False}]
    db.write_text(json.dumps(valid_todos), encoding="utf-8")

    # Verify it's a regular file, not a symlink
    assert not db.is_symlink(), "Test setup failed: db should not be a symlink"
    assert db.is_file(), "Test setup failed: db should be a regular file"

    # load() should work normally
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "normal todo"


def test_load_returns_empty_for_nonexistent_file(tmp_path) -> None:
    """Issue #6896: load() should return empty list for nonexistent file.

    This is a regression test to ensure the fix doesn't change existing behavior.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Verify file doesn't exist
    assert not db.exists(), "Test setup failed: db should not exist"

    # load() should return empty list
    todos = storage.load()
    assert todos == []


def test_load_rejects_broken_symlink(tmp_path) -> None:
    """Issue #6896: load() should reject broken symlinks (symlink to nonexistent target).

    This ensures proper error handling for broken symlinks.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a symlink pointing to a nonexistent target
    nonexistent_target = tmp_path / "does_not_exist.json"
    if db.exists():
        db.unlink()
    db.symlink_to(nonexistent_target)

    # Verify it's a symlink (even though target doesn't exist)
    assert db.is_symlink(), "Test setup failed: db should be a symlink"

    # load() should reject the symlink, not fail trying to read the nonexistent target
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_rejects_symlink_to_directory(tmp_path) -> None:
    """Issue #6896: load() should reject symlinks pointing to directories.

    This ensures the check handles all symlink types.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a symlink pointing to a directory
    target_dir = tmp_path / "some_directory"
    target_dir.mkdir()

    if db.exists():
        db.unlink()
    db.symlink_to(target_dir)

    # Verify it's a symlink
    assert db.is_symlink(), "Test setup failed: db should be a symlink"

    # load() should reject the symlink with a clear ValueError
    # (not IsADirectoryError which would happen if we tried to read the symlink)
    with pytest.raises(ValueError, match="symlink"):
        storage.load()

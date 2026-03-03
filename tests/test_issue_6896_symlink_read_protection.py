"""Regression tests for issue #6896: Symlink read protection in load().

Issue: The load() method follows symlinks when reading the database file,
allowing an attacker who can create a symlink at the db path to read arbitrary
files through the application's error messages or data loading.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_symlink_pointing_to_regular_file(tmp_path) -> None:
    """Issue #6896: load() should reject symlinks to prevent arbitrary file read.

    Before fix: load() follows symlink and reads content of target file
    After fix: load() should raise ValueError when db path is a symlink
    """
    # Create a target file with valid JSON content (attacker could craft this)
    # to demonstrate that even valid JSON should be rejected when accessed via symlink
    sensitive_file = tmp_path / "sensitive_data.json"
    sensitive_file.write_text(json.dumps([{"id": 1, "text": "EXPOSED_SECRET_DATA"}]))

    # Create a symlink at the db path pointing to the sensitive file
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(sensitive_file)

    storage = TodoStorage(str(db_symlink))

    # Before fix: This would read the sensitive file content and return todos
    # After fix: This should raise ValueError about symlinks
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_rejects_symlink_pointing_to_json_file(tmp_path) -> None:
    """Issue #6896: load() should reject symlinks even to valid JSON files.

    This prevents attackers from redirecting the db path to any file,
    even if it happens to be valid JSON.
    """
    # Create a target JSON file with todo data
    target_json = tmp_path / "real_todo.json"
    target_json.write_text(json.dumps([{"id": 1, "text": "legitimate todo"}]))

    # Create a symlink at the db path pointing to the real JSON
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(target_json)

    storage = TodoStorage(str(db_symlink))

    # Even though it's valid JSON, we should reject symlinks
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_rejects_broken_symlink(tmp_path) -> None:
    """Issue #6896: load() should reject symlinks even if target doesn't exist."""
    # Create a symlink pointing to non-existent target
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(tmp_path / "non_existent_file.json")

    storage = TodoStorage(str(db_symlink))

    # Should raise ValueError about symlink, not FileNotFoundError
    with pytest.raises(ValueError, match="symlink"):
        storage.load()


def test_load_accepts_regular_file(tmp_path) -> None:
    """Issue #6896: load() should still work with regular files after fix."""
    db = tmp_path / "todo.json"
    db.write_text(json.dumps([{"id": 1, "text": "test todo", "done": False}]))

    storage = TodoStorage(str(db))

    # Should load normally without raising symlink error
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "test todo"
    assert todos[0].done is False


def test_load_returns_empty_list_for_non_existent_file(tmp_path) -> None:
    """Issue #6896: load() should return empty list for non-existent files."""
    db = tmp_path / "non_existent.json"
    storage = TodoStorage(str(db))

    # Should return empty list, not raise symlink error
    todos = storage.load()
    assert todos == []


def test_symlink_protection_error_message_is_clear(tmp_path) -> None:
    """Issue #6896: Error message should clearly explain the symlink rejection."""
    # Create a target file
    target = tmp_path / "target.txt"
    target.write_text("some content")

    # Create symlink
    db_symlink = tmp_path / "todo.json"
    db_symlink.symlink_to(target)

    storage = TodoStorage(str(db_symlink))

    try:
        storage.load()
        pytest.fail("Expected ValueError to be raised")
    except ValueError as e:
        error_msg = str(e).lower()
        # Error message should mention symlink and security concern
        assert "symlink" in error_msg, f"Error message should mention symlink: {e}"
        # Should be informative about why it was rejected
        assert "security" in error_msg or "not allowed" in error_msg or "rejected" in error_msg, \
            f"Error message should explain security concern: {e}"


def test_symlink_protection_with_symlink_in_parent_directory(tmp_path) -> None:
    """Issue #6896: load() should work when parent directory is a symlink.

    We only reject when the db file itself is a symlink, not when
    parent directories contain symlinks.
    """
    # Create a real directory and a symlink to it
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    symlink_dir = tmp_path / "symlink_dir"
    symlink_dir.symlink_to(real_dir)

    # Create a valid db file in the symlinked directory
    db = symlink_dir / "todo.json"
    db.write_text(json.dumps([{"id": 1, "text": "test"}]))

    storage = TodoStorage(str(db))

    # This should work - only the db file itself should be checked
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "test"
